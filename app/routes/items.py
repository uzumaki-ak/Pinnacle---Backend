from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from loguru import logger
import uuid
from datetime import datetime

from app.models.item import (
    ItemCreate, ItemUpdate, ItemResponse, BulkOperation,
    ItemFilter, ItemStats, ExportRequest
)
from app.routes.auth import get_current_user
from app.services.extraction_service import extraction_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from app.utils.deduplication import check_duplicate
from supabase import create_client
from app.config import settings

router = APIRouter()

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

@router.post("/", response_model=ItemResponse)
async def create_item(
    item: ItemCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create a new saved item"""
    try:
        user_id = current_user["id"]
        
        # Check for duplicates if enabled
        if settings.ENABLE_DUPLICATE_DETECTION:
            duplicate = await check_duplicate(user_id, item.url)
            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail=f"Item already exists with ID: {duplicate['id']}"
                )
        
        # Create item record
        item_id = str(uuid.uuid4())
        item_data = {
            "id": item_id,
            "user_id": user_id,
            "title": item.title,
            "url": item.url,
            "media_type": item.media_type.value,
            "folders": item.folders,
            "tags": item.tags,
            "note": item.note,
            "description": item.description,
            "extraction_status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("items").insert(item_data).execute()
        
        # Extract content in background
        if item.extract_content:
            background_tasks.add_task(
                process_item_content,
                item_id,
                user_id,
                item.url,
                item.title,
                item.auto_transcribe,
                item.auto_ocr
            )
        
        return ItemResponse(**result.data[0])
        
    except Exception as e:
        logger.error(f"Failed to create item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_item_content(
    item_id: str,
    user_id: str,
    url: str,
    title: str,
    auto_transcribe: bool,
    auto_ocr: bool
):
    """Background task to extract and embed content"""
    try:
        # Update status
        supabase.table("items")\
            .update({"extraction_status": "processing"})\
            .eq("id", item_id)\
            .execute()
        
        # Extract content
        content_data = await extraction_service.extract_content(url)
        
        # Generate auto-tags if enabled
        tags = []
        if settings.ENABLE_AUTO_TAGGING and content_data.get("content"):
            tags = await llm_service.generate_tags(
                title,
                content_data.get("content", "")[:1000],
                url
            )
        
        # Generate summary
        summary = None
        if content_data.get("content"):
            summary = await llm_service.generate_summary(
                content_data.get("content", "")
            )
        
        # Extract favicon
        favicon_url = await extraction_service.extract_favicon(url)
        
        # Update item with extracted data
        update_data = {
            "content_snippet": summary or content_data.get("description", ""),
            "source_metadata": {
                "author": content_data.get("author"),
                "published_date": str(content_data.get("published_date")) if content_data.get("published_date") else None,
                "domain": content_data.get("domain"),
                "image": content_data.get("image") or content_data.get("thumbnail"),
                "word_count": content_data.get("word_count", 0)
            },
            "favicon_url": favicon_url,
            "thumbnail_url": content_data.get("image") or content_data.get("thumbnail"),
            "extraction_status": "completed"
        }
        
        # Add auto-generated tags
        if tags:
            existing_item = supabase.table("items").select("tags").eq("id", item_id).single().execute()
            existing_tags = existing_item.data.get("tags", [])
            combined_tags = list(set(existing_tags + tags))
            update_data["tags"] = combined_tags
        
        supabase.table("items").update(update_data).eq("id", item_id).execute()
        
        # Generate embeddings if content available
        if content_data.get("content"):
            chunks = await embedding_service.process_content_for_rag(
                content_data["content"]
            )
            
            if chunks:
                await vector_service.store_embeddings(item_id, user_id, chunks)
                logger.info(f"Generated {len(chunks)} embeddings for item {item_id}")
        
        logger.success(f"✅ Processed item {item_id}")
        
    except Exception as e:
        logger.error(f"Failed to process item content: {e}")
        supabase.table("items")\
            .update({"extraction_status": "failed"})\
            .eq("id", item_id)\
            .execute()

@router.get("/", response_model=List[ItemResponse])
async def get_items(
    media_types: Optional[str] = None,
    folders: Optional[str] = None,
    tags: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get user's items with filters"""
    try:
        user_id = current_user["id"]
        
        query = supabase.table("items").select("*").eq("user_id", user_id)
        
        # Apply filters
        if media_types:
            types_list = media_types.split(",")
            query = query.in_("media_type", types_list)
        
        if folders:
            folders_list = folders.split(",")
            query = query.overlaps("folders", folders_list)
        
        if tags:
            tags_list = tags.split(",")
            query = query.overlaps("tags", tags_list)
        
        if search:
            query = query.ilike("title", f"%{search}%")
        
        # Order and paginate
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        return [ItemResponse(**item) for item in result.data]
        
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific item"""
    try:
        result = supabase.table("items")\
            .select("*")\
            .eq("id", item_id)\
            .eq("user_id", current_user["id"])\
            .single()\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Update accessed_at
        supabase.table("items")\
            .update({"accessed_at": datetime.utcnow().isoformat()})\
            .eq("id", item_id)\
            .execute()
        
        return ItemResponse(**result.data)
        
    except Exception as e:
        logger.error(f"Failed to fetch item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    item: ItemUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an item"""
    try:
        update_data = item.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        result = supabase.table("items")\
            .update(update_data)\
            .eq("id", item_id)\
            .eq("user_id", current_user["id"])\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return ItemResponse(**result.data[0])
        
    except Exception as e:
        logger.error(f"Failed to update item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{item_id}")
async def delete_item(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an item"""
    try:
        # Delete embeddings first
        await vector_service.delete_embeddings(item_id)
        
        # Delete item
        result = supabase.table("items")\
            .delete()\
            .eq("id", item_id)\
            .eq("user_id", current_user["id"])\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {"message": "Item deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk")
async def bulk_operation(
    operation: BulkOperation,
    current_user: dict = Depends(get_current_user)
):
    """Perform bulk operations on items"""
    try:
        user_id = current_user["id"]
        
        if operation.operation == "delete":
            for item_id in operation.item_ids:
                await vector_service.delete_embeddings(item_id)
            
            supabase.table("items")\
                .delete()\
                .in_("id", operation.item_ids)\
                .eq("user_id", user_id)\
                .execute()
            
            return {"message": f"Deleted {len(operation.item_ids)} items"}
        
        elif operation.operation == "add_tag":
            # Add tag to all items
            for item_id in operation.item_ids:
                item = supabase.table("items").select("tags").eq("id", item_id).single().execute()
                tags = item.data.get("tags", [])
                if operation.value not in tags:
                    tags.append(operation.value)
                supabase.table("items").update({"tags": tags}).eq("id", item_id).execute()
            
            return {"message": f"Added tag to {len(operation.item_ids)} items"}
        
        # Add more operations as needed
        
    except Exception as e:
        logger.error(f"Bulk operation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metadata/folders")
async def get_folders(current_user: dict = Depends(get_current_user)):
    """Get all unique folders for the user"""
    try:
        user_id = current_user["id"]
        
        items = supabase.table("items").select("folders").eq("user_id", user_id).execute()
        
        all_folders = set()
        for item in items.data:
            all_folders.update(item.get("folders", []))
        
        return {
            "folders": sorted(list(all_folders))
        }
        
    except Exception as e:
        logger.error(f"Failed to get folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metadata/tags")
async def get_tags(current_user: dict = Depends(get_current_user)):
    """Get all unique tags for the user"""
    try:
        user_id = current_user["id"]
        
        items = supabase.table("items").select("tags").eq("user_id", user_id).execute()
        
        all_tags = set()
        for item in items.data:
            all_tags.update(item.get("tags", []))
        
        return {
            "tags": sorted(list(all_tags))
        }
        
    except Exception as e:
        logger.error(f"Failed to get tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/overview", response_model=ItemStats)
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Get user's item statistics"""
    try:
        user_id = current_user["id"]
        
        # Get all items
        items = supabase.table("items").select("*").eq("user_id", user_id).execute()
        
        # Calculate stats
        total_items = len(items.data)
        items_by_type = {}
        all_folders = set()
        all_tags = set()
        
        for item in items.data:
            media_type = item.get("media_type", "other")
            items_by_type[media_type] = items_by_type.get(media_type, 0) + 1
            all_folders.update(item.get("folders", []))
            all_tags.update(item.get("tags", []))
        
        return ItemStats(
            total_items=total_items,
            items_by_type=items_by_type,
            total_folders=len(all_folders),
            total_tags=len(all_tags),
            storage_used_mb=0.0,  # Calculate if storing files
            last_saved=items.data[0]["created_at"] if items.data else None
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))