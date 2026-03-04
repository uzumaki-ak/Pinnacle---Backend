from sentence_transformers import SentenceTransformer
from typing import List, Union
from loguru import logger
import numpy as np
import asyncio
from functools import lru_cache

from app.config import settings

class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS
    
    async def load_model(self):
        """Load the embedding model"""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                SentenceTransformer,
                self.model_name
            )
            logger.success(f"✅ Embedding model loaded successfully")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if self.model is None:
            await self.load_model()
        
        # Run encoding in thread pool
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self.model.encode,
            text
        )
        
        return embedding.tolist()
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batched)"""
        if self.model is None:
            await self.load_model()
        
        # Run batch encoding in thread pool
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self.model.encode,
            texts
        )
        
        return embeddings.tolist()
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending punctuation
                for i in range(end, max(start, end - 100), -1):
                    if text[i] in '.!?\n':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    async def process_content_for_rag(
        self,
        content: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[dict]:
        """
        Process content into chunks with embeddings for RAG
        
        Returns list of dicts with 'text', 'embedding', 'chunk_index'
        """
        # Split into chunks
        chunks = self.chunk_text(content, chunk_size, overlap)
        
        # Generate embeddings for all chunks
        embeddings = await self.generate_embeddings(chunks)
        
        # Combine into result
        result = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            result.append({
                "text": chunk,
                "embedding": embedding,
                "chunk_index": idx,
                "chunk_id": f"chunk_{idx}"
            })
        
        return result
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return float(dot_product / (norm_v1 * norm_v2))

# Global instance
embedding_service = EmbeddingService()

async def init_embedding_model():
    """Initialize embedding model at startup"""
    await embedding_service.load_model()