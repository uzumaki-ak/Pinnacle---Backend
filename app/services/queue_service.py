import redis.asyncio as redis
from typing import Optional, Dict, Any
from loguru import logger
import json

from app.config import settings

class QueueService:
    """Redis queue service for background jobs"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                ssl_cert_reqs=None  # Required for Upstash TLS
            )
            await self.redis_client.ping()
            logger.success("✅ Connected to Redis")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def enqueue(self, queue_name: str, data: Dict[str, Any]) -> bool:
        """Add job to queue"""
        try:
            if not self.redis_client:
                await self.connect()
            
            job_data = json.dumps(data)
            await self.redis_client.lpush(queue_name, job_data)
            logger.info(f"Job enqueued to {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue job: {e}")
            return False
    
    async def dequeue(self, queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """Get job from queue (blocking)"""
        try:
            if not self.redis_client:
                await self.connect()
            
            result = await self.redis_client.brpop(queue_name, timeout=timeout)
            if result:
                _, job_data = result
                return json.loads(job_data)
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue job: {e}")
            return None
    
    async def get_queue_length(self, queue_name: str) -> int:
        """Get number of jobs in queue"""
        try:
            if not self.redis_client:
                await self.connect()
            return await self.redis_client.llen(queue_name)
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0
    
    async def clear_queue(self, queue_name: str):
        """Clear all jobs from queue"""
        try:
            if not self.redis_client:
                await self.connect()
            await self.redis_client.delete(queue_name)
            logger.info(f"Queue {queue_name} cleared")
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")

queue_service = QueueService()

async def init_queue():
    """Initialize queue service"""
    await queue_service.connect()

async def shutdown_queue():
    """Shutdown queue service"""
    await queue_service.disconnect()