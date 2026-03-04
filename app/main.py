from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import settings
from app.routes import items, chat, auth, extract, share
from app.services.queue_service import init_queue, shutdown_queue
from app.services.embedding_service import init_embedding_model

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting Content Vault Backend...")
    
    # Initialize services
    try:
        # Init embedding model
        logger.info("Loading embedding model...")
        await init_embedding_model()
        
        # Init queue system
        logger.info("Connecting to Redis queue...")
        await init_queue()
        
        logger.success("✅ All services initialized successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Content Vault Backend...")
    await shutdown_queue()
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Content Vault API",
    description="Save, organize, and chat with your web content using RAG",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.ENVIRONMENT == "development" else "Something went wrong"
        }
    )

# Health check
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Content Vault API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "redis": "connected",
            "embedding_model": "loaded"
        }
    }

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(items.router, prefix="/api/v1/items", tags=["Items"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat & RAG"])
app.include_router(extract.router, prefix="/api/v1/extract", tags=["Content Extraction"])
app.include_router(share.router, prefix="/api/v1/share", tags=["Sharing"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )