from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from loguru import logger
from supabase import create_client

from app.config import settings
import os

# Clear proxy env vars
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

# Monkey-patch gotrue to fix httpx proxy parameter compatibility issue
# The issue is that gotrue passes proxy=None to httpx.Client, but httpx doesn't accept None
try:
    from gotrue._sync import gotrue_base_api
    from gotrue.http_clients import SyncClient as GotrueSyncClient
    import httpx
    
    # Patch SyncClient creation to handle None proxy
    original_sync_client_init = GotrueSyncClient.__init__
    
    def patched_sync_client_init(self, *args, **kwargs):
        # Remove proxy from kwargs if it's None
        if 'proxy' in kwargs and kwargs['proxy'] is None:
            kwargs.pop('proxy')
        return original_sync_client_init(self, *args, **kwargs)
    
    GotrueSyncClient.__init__ = patched_sync_client_init
    
    # Also patch the base API to ensure it doesn't pass None proxy
    original_base_init = gotrue_base_api.SyncGoTrueBaseAPI.__init__
    
    def patched_base_init(self, *, url, headers, http_client, verify=True, proxy=None, **kwargs):
        self._url = url
        self._headers = headers
        
        if http_client is None:
            # Only pass proxy if it's not None
            client_kwargs = {
                'verify': bool(verify),
                'follow_redirects': True,
                'http2': True,
            }
            if proxy is not None:
                client_kwargs['proxy'] = proxy
            
            http_client = GotrueSyncClient(**client_kwargs)
        
        self._http_client = http_client
    
    gotrue_base_api.SyncGoTrueBaseAPI.__init__ = patched_base_init
except Exception as e:
    logger.warning(f"Failed to patch gotrue: {e}")

router = APIRouter()
security = HTTPBearer()

# Initialize Supabase
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency to get current authenticated user from JWT token
    """
    try:
        token = credentials.credentials
        
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )
        
        return {
            "id": user_response.user.id,
            "email": user_response.user.email,
            "user_metadata": user_response.user.user_metadata
        }
        
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )

@router.post("/signup", response_model=AuthResponse)
async def sign_up(request: SignUpRequest):
    """Register a new user"""
    try:
        # Sign up with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "full_name": request.full_name
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=400,
                detail="Failed to create account"
            )
        
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "full_name": request.full_name
            }
        )
        
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest):
    """Sign in existing user"""
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            user={
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "full_name": auth_response.user.user_metadata.get("full_name")
            }
        )
        
    except Exception as e:
        logger.error(f"Signin error: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/signout")
async def sign_out(current_user: dict = Depends(get_current_user)):
    """Sign out current user"""
    try:
        supabase.auth.sign_out()
        return {"message": "Signed out successfully"}
    except Exception as e:
        logger.error(f"Signout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return current_user