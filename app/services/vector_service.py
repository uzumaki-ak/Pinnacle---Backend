from supabase import create_client, Client
from typing import List, Dict, Any, Optional
from loguru import logger
import uuid

from app.config import settings

class VectorService:
    """Service for vector database operations using Supabase pgvector"""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    async def store_embeddings(
        self,
        item_id: str,
        user_id: str,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store content chunks with embeddings in vector database
        
        Args:
            item_id: ID of the parent item
            user_id: User ID
            chunks: List of dicts with 'text', 'embedding', 'chunk_index', 'chunk_id'
        
        Returns:
            List of inserted embedding IDs
        """
        try:
            if not chunks:
                logger.warning(f"No chunks to store for item {item_id}")
                return []
            
            records = []
            embedding_ids = []
            
            for chunk in chunks:
                if not chunk.get("text") or not chunk.get("embedding"):
                    logger.warning(f"Skipping invalid chunk for item {item_id}")
                    continue
                    
                embedding_id = str(uuid.uuid4())
                embedding_ids.append(embedding_id)
                
                # Validate embedding dimensions
                embedding = chunk.get("embedding")
                if isinstance(embedding, list):
                    if len(embedding) != 384:
                        logger.warning(f"⚠️ Embedding has {len(embedding)} dimensions, expected 384")
                
                records.append({
                    "id": embedding_id,
                    "item_id": item_id,
                    "user_id": user_id,
                    "chunk_id": chunk.get("chunk_id", f"chunk_{len(records)}"),
                    "chunk_index": chunk.get("chunk_index", len(records)),
                    "content": chunk["text"][:5000],  # Limit to 5000 chars
                    "embedding": embedding
                })
            
            if not records:
                logger.error(f"No valid records to insert for item {item_id}")
                return []
            
            # Insert into embeddings table
            logger.info(f"💾 Storing {len(records)} embeddings for item {item_id}...")
            result = self.client.table("embeddings").insert(records).execute()
            
            logger.success(f"✅ Stored {len(records)} embeddings for item {item_id}")
            return embedding_ids
            
        except Exception as e:
            logger.error(f"❌ Failed to store embeddings: {e}")
            logger.error(f"   Item ID: {item_id}, User ID: {user_id}, Chunk count: {len(chunks)}")
            raise
    
    async def search_similar(
        self,
        query_embedding: List[float],
        user_id: str,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content chunks using vector similarity
        """
        try:
            logger.info(f"🔎 Search params - user_id: {user_id}, threshold: {similarity_threshold}, limit: {limit}")
            logger.info(f"🔎 Embedding dims: {len(query_embedding)}")
            
            # Always use fallback - RPC has issues with vector parameter passing
            return await self._search_similar_fallback(
                query_embedding, user_id, limit, similarity_threshold
            )
            
        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}")
            return []
    
    async def _search_similar_fallback(
        self,
        query_embedding: List[float],
        user_id: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Fallback search using raw SQL instead of RPC"""
        try:
            import numpy as np
            import json
            
            result = self.client.table("embeddings")\
                .select("*, items(*)")\
                .eq("user_id", user_id)\
                .limit(100)\
                .execute()
            
            logger.info(f"📦 Fetched {len(result.data)} embeddings from DB")
            
            scores = []
            query_vec = np.array(query_embedding, dtype=np.float32)
            
            for chunk in result.data:
                try:
                    emb = chunk.get("embedding")
                    if isinstance(emb, str):
                        emb = json.loads(emb)
                    
                    chunk_vec = np.array(emb, dtype=np.float32)
                    
                    dot = float(np.dot(query_vec, chunk_vec))
                    norm_q = float(np.linalg.norm(query_vec))
                    norm_c = float(np.linalg.norm(chunk_vec))
                    
                    if norm_q > 0 and norm_c > 0:
                        similarity = dot / (norm_q * norm_c)
                        
                        logger.info(f"   Chunk {chunk.get('chunk_id')}: similarity={similarity:.4f}, pass={similarity >= similarity_threshold}")
                        
                        if similarity >= similarity_threshold:
                            scores.append({
                                "id": chunk.get("id"),
                                "item_id": chunk.get("item_id"),
                                "chunk_id": chunk.get("chunk_id"),
                                "chunk_index": chunk.get("chunk_index"),
                                "content": chunk.get("content"),
                                "similarity": float(similarity),
                                "item_title": chunk.get("items", {}).get("title") if chunk.get("items") else None,
                                "item_url": chunk.get("items", {}).get("url") if chunk.get("items") else None,
                                "item_folders": chunk.get("items", {}).get("folders", []) if chunk.get("items") else [],
                                "item_tags": chunk.get("items", {}).get("tags", []) if chunk.get("items") else []
                            })
                except Exception as e:
                    logger.warning(f"Chunk error: {e}")
                    continue
            
            scores.sort(key=lambda x: x["similarity"], reverse=True)
            logger.info(f"✅ Fallback found {len(scores)} results >= {similarity_threshold}")
            return scores[:limit]
            
        except Exception as e:
            logger.error(f"❌ Fallback failed: {e}")
            raise
    
    async def delete_embeddings(self, item_id: str) -> bool:
        """Delete all embeddings for an item"""
        try:
            result = self.client.table("embeddings")\
                .delete()\
                .eq("item_id", item_id)\
                .execute()
            
            logger.info(f"Deleted embeddings for item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete embeddings: {e}")
            return False
    
    async def get_item_with_metadata(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item with all metadata for RAG context"""
        try:
            result = self.client.table("items")\
                .select("*, embeddings(*)")\
                .eq("id", item_id)\
                .single()\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to fetch item metadata: {e}")
            return None

# Global instance
vector_service = VectorService()

# SQL function to create in Supabase (run this once in SQL editor):
"""
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    chunk_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),  -- Match your embedding dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx 
ON embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index for item_id lookups
CREATE INDEX IF NOT EXISTS embeddings_item_id_idx ON embeddings(item_id);

-- Create index for user_id lookups
CREATE INDEX IF NOT EXISTS embeddings_user_id_idx ON embeddings(user_id);

-- Vector similarity search function
CREATE OR REPLACE FUNCTION match_embeddings (
    query_embedding vector(384),
    match_user_id UUID,
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE (
    id UUID,
    item_id UUID,
    chunk_id TEXT,
    chunk_index INT,
    content TEXT,
    similarity FLOAT,
    item_title TEXT,
    item_url TEXT,
    item_folders TEXT[],
    item_tags TEXT[]
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.item_id,
        e.chunk_id,
        e.chunk_index,
        e.content,
        1 - (e.embedding <=> query_embedding) AS similarity,
        i.title AS item_title,
        i.url AS item_url,
        i.folders AS item_folders,
        i.tags AS item_tags
    FROM embeddings e
    JOIN items i ON e.item_id = i.id
    WHERE e.user_id = match_user_id
    AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""