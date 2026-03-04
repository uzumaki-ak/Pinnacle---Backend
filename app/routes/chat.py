from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from loguru import logger

from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.routes.auth import get_current_user

router = APIRouter()

class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 1000
    use_rag: bool = True
    filters: Optional[Dict[str, Any]] = None  # folders, tags, media_types

class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    sources: List[Dict[str, Any]] = []

class RAGQueryRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 5

@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    user_api_keys: Optional[str] = Header(None, alias="X-User-API-Keys")
):
    """
    Send a chat message with optional RAG retrieval
    """
    try:
        user_id = current_user["id"]
        
        # Parse user API keys if provided
        api_keys = None
        if user_api_keys:
            try:
                import json
                api_keys = json.loads(user_api_keys)
            except:
                pass
        
        # If RAG is enabled, retrieve relevant context
        sources = []
        if request.use_rag and len(request.messages) > 0:
            last_message = request.messages[-1].content
            
            # Generate embedding for query
            logger.info(f"🔍 Generating embedding for query: {last_message[:50]}...")
            query_embedding = await embedding_service.generate_embedding(last_message)
            logger.info(f"✅ Query embedding generated: {len(query_embedding)} dimensions")
            
            # Search similar content
            logger.info(f"🔍 Searching for similar chunks in vector DB...")
            similar_chunks = await vector_service.search_similar(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=request.filters.get("top_k", 5) if request.filters else 5,
                similarity_threshold=0.1
            )
            
            logger.info(f"📊 Found {len(similar_chunks)} similar chunks")
            
            if similar_chunks:
                logger.info(f"✅ Top match similarity: {similar_chunks[0].get('similarity', 0)}")
            
            # Build context from retrieved chunks
            if similar_chunks:
                context_parts = []
                for idx, chunk in enumerate(similar_chunks):
                    context_parts.append(
                        f"[Source {idx+1}: {chunk.get('item_title', 'Unknown')}]\n"
                        f"Folder: {' > '.join(chunk.get('item_folders', []))}\n"
                        f"Tags: {', '.join(chunk.get('item_tags', []))}\n"
                        f"Content: {chunk.get('content', '')}\n"
                    )
                    
                    sources.append({
                        "item_id": chunk.get("item_id"),
                        "title": chunk.get("item_title"),
                        "url": chunk.get("item_url"),
                        "folders": chunk.get("item_folders", []),
                        "tags": chunk.get("item_tags", []),
                        "similarity": chunk.get("similarity", 0),
                        "chunk_index": chunk.get("chunk_index", 0)
                    })
                
                context = "\n\n".join(context_parts)
                
                # Add context to messages
                system_message = {
                    "role": "system",
                    "content": f"""You are a helpful assistant that answers questions based on the user's saved content.
                    
Use the following retrieved content to answer the user's question. Always cite which source you're using.
If you mention a specific item, include its folder path and tags.

Retrieved Content:
{context}

If the retrieved content doesn't contain the answer, say so politely."""
                }
                
                # Insert system message at the beginning
                messages = [system_message] + [
                    {"role": msg.role, "content": msg.content} 
                    for msg in request.messages
                ]
            else:
                messages = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in request.messages
                ]
        else:
            messages = [
                {"role": msg.role, "content": msg.content} 
                for msg in request.messages
            ]
        
        # Get completion from LLM
        response = await llm_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            user_api_keys=api_keys
        )
        
        return ChatResponse(
            content=response["content"],
            provider=response["provider"],
            model=response["model"],
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag-search")
async def rag_search(
    request: RAGQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Perform RAG search without generating a response
    Returns relevant sources for a query
    """
    try:
        user_id = current_user["id"]
        
        # Generate embedding
        query_embedding = await embedding_service.generate_embedding(request.query)
        
        # Search similar
        results = await vector_service.search_similar(
            query_embedding=query_embedding,
            user_id=user_id,
            limit=request.top_k,
            similarity_threshold=0.5
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-tags")
async def generate_tags_endpoint(
    title: str,
    content: str,
    url: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate tags for content using LLM"""
    try:
        tags = await llm_service.generate_tags(title, content, url)
        return {"tags": tags}
    except Exception as e:
        logger.error(f"Tag generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
