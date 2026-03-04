import asyncio
from loguru import logger

from app.services.queue_service import queue_service
from app.services.extraction_service import extraction_service
from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service
from app.config import settings
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

async def process_extraction_job(job_data: dict):
    """Process content extraction job"""
    item_id = job_data.get("item_id")
    user_id = job_data.get("user_id")
    url = job_data.get("url")
    
    logger.info(f"Processing extraction for item {item_id}")
    
    try:
        # Extract content
        content_data = await extraction_service.extract_content(url)
        
        # Update item with extracted data
        update_data = {
            "content_snippet": content_data.get("content", "")[:500],
            "source_metadata": content_data,
            "extraction_status": "completed"
        }
        
        supabase.table("items").update(update_data).eq("id", item_id).execute()
        
        # Generate embeddings
        if content_data.get("content"):
            chunks = await embedding_service.process_content_for_rag(content_data["content"])
            if chunks:
                await vector_service.store_embeddings(item_id, user_id, chunks)
        
        logger.success(f"✅ Extraction completed for item {item_id}")
        
    except Exception as e:
        logger.error(f"❌ Extraction failed for item {item_id}: {e}")
        supabase.table("items").update({"extraction_status": "failed"}).eq("id", item_id).execute()

async def run_extraction_worker():
    """Run extraction worker continuously"""
    logger.info("🚀 Starting extraction worker...")
    
    while True:
        try:
            # Get job from queue
            job = await queue_service.dequeue(settings.QUEUE_EXTRACTION, timeout=5)
            
            if job:
                await process_extraction_job(job)
            else:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_extraction_worker())