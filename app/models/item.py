from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MediaType(str, Enum):
    LINK = "link"
    ARTICLE = "article"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    PDF = "pdf"
    OTHER = "other"

class ItemBase(BaseModel):
    title: str
    url: str
    media_type: MediaType
    folders: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    description: Optional[str] = None

class ItemCreate(ItemBase):
    """Schema for creating a new item"""
    extract_content: bool = True
    auto_transcribe: bool = True
    auto_ocr: bool = True

class ItemUpdate(BaseModel):
    """Schema for updating an item"""
    title: Optional[str] = None
    folders: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    description: Optional[str] = None

class ContentChunk(BaseModel):
    """Represents a chunk of extracted content"""
    chunk_id: str
    text: str
    embedding_id: Optional[str] = None
    source_range: Optional[str] = None
    chunk_index: int

class ItemResponse(ItemBase):
    """Schema for item response"""
    id: str
    user_id: str
    content_snippet: Optional[str] = None
    content_chunks: List[ContentChunk] = Field(default_factory=list)
    storage_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    favicon_url: Optional[str] = None
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    extraction_status: str = "pending"  # pending, processing, completed, failed
    transcription_status: Optional[str] = None
    ocr_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    accessed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class BulkOperation(BaseModel):
    """Schema for bulk operations"""
    item_ids: List[str]
    operation: str  # delete, add_tag, remove_tag, move_folder, export
    value: Optional[Any] = None  # tag name, folder name, etc.

class ItemFilter(BaseModel):
    """Schema for filtering items"""
    media_types: Optional[List[MediaType]] = None
    folders: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 50
    offset: int = 0

class ItemStats(BaseModel):
    """Statistics about user's items"""
    total_items: int
    items_by_type: Dict[str, int]
    total_folders: int
    total_tags: int
    storage_used_mb: float
    last_saved: Optional[datetime] = None

class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"

class ExportRequest(BaseModel):
    format: ExportFormat
    item_ids: Optional[List[str]] = None  # If None, export all
    include_content: bool = True
    include_metadata: bool = True