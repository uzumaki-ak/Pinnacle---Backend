from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from supabase import create_client
import secrets

from app.config import settings
from app.routes.auth import get_current_user

router = APIRouter()
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

class ShareRequest(BaseModel):
    item_id: str
    is_public: bool = True
    expires_in_days: Optional[int] = None

class ShareResponse(BaseModel):
    share_url: str
    share_token: str
    expires_at: Optional[datetime]

@router.post("/create", response_model=ShareResponse)
async def create_share_link(
    request: ShareRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create shareable link for an item"""
    user_id = current_user["id"]
    
    # Verify ownership
    item = supabase.table("items").select("*").eq("id", request.item_id).eq("user_id", user_id).single().execute()
    if not item.data:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Generate token
    share_token = secrets.token_urlsafe(32)
    
    # Calculate expiry
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    # Create share record
    share_data = {
        "item_id": request.item_id,
        "user_id": user_id,
        "share_token": share_token,
        "is_public": request.is_public,
        "expires_at": expires_at.isoformat() if expires_at else None
    }
    
    supabase.table("shared_items").insert(share_data).execute()
    
    share_url = f"{settings.SUPABASE_URL}/share/{share_token}"
    
    return ShareResponse(
        share_url=share_url,
        share_token=share_token,
        expires_at=expires_at
    )

@router.get("/{share_token}")
async def get_shared_item(share_token: str):
    """Get shared item by token"""
    share = supabase.table("shared_items").select("*, items(*)").eq("share_token", share_token).single().execute()
    
    if not share.data:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    # Check expiry
    if share.data.get("expires_at"):
        expires_at = datetime.fromisoformat(share.data["expires_at"])
        if datetime.utcnow() > expires_at:
            raise HTTPException(status_code=410, detail="Share link expired")
    
    return share.data["items"]

@router.delete("/{share_token}")
async def delete_share_link(
    share_token: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete share link"""
    user_id = current_user["id"]
    
    result = supabase.table("shared_items").delete().eq("share_token", share_token).eq("user_id", user_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    return {"message": "Share link deleted"}