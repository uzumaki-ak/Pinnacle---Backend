from pydantic import BaseModel
from typing import List
from datetime import datetime

class EmbeddingCreate(BaseModel):
    item_id: str
    user_id: str
    chunk_id: str
    chunk_index: int
    content: str
    embedding: List[float]

class EmbeddingResponse(BaseModel):
    id: str
    item_id: str
    chunk_id: str
    chunk_index: int
    content: str
    created_at: datetime
    
class SimilaritySearchResult(BaseModel):
    id: str
    item_id: str
    chunk_id: str
    content: str
    similarity: float
    item_title: str
    item_url: str
    item_folders: List[str]
    item_tags: List[str]