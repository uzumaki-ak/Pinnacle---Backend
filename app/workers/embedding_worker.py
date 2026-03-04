import asyncio
from loguru import logger

from app.services.queue_service import queue_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.config import settings

async def process_embedding_job(job_data: dict):
    """Process embedding generation job"""
    item_id = job_data.get("item_id")
    user_id = job_data.get("user_id")
    content = job_data.get("content")
    
    logger.info(f"Generating embeddings for item {item_id}")
    
    try:
        chunks = await embedding_service.process_content_for_rag(content)
        
        if chunks:
            await vector_service.store_embeddings(item_id, user_id, chunks)
            logger.success(f"✅ Generated {len(chunks)} embeddings for item {item_id}")
        else:
            logger.warning(f"No chunks generated for item {item_id}")
            
    except Exception as e:
        logger.error(f"❌ Embedding generation failed for item {item_id}: {e}")

async def run_embedding_worker():
    """Run embedding worker continuously"""
    logger.info("🚀 Starting embedding worker...")
    
    while True:
        try:
            job = await queue_service.dequeue(settings.QUEUE_EMBEDDING, timeout=5)
            
            if job:
                await process_embedding_job(job)
            else:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_embedding_worker())