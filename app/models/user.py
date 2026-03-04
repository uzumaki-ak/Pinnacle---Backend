from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class UserPreferences(BaseModel):
    """User preferences and settings"""
    theme: str = "light"
    default_folder: Optional[str] = None
    auto_extract: bool = True
    auto_transcribe: bool = True
    auto_ocr: bool = True
    auto_tag: bool = True
    notification_enabled: bool = True
    
class UserAPIKeys(BaseModel):
    """User's custom API keys"""
    groq_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
class UserProfile(BaseModel):
    """User profile information"""
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: UserPreferences = UserPreferences()
    api_keys: Optional[UserAPIKeys] = None
    created_at: datetime
    updated_at: datetime