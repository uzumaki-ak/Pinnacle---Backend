from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Server
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    API_VERSION: str = "v1"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: str
    DATABASE_URL: str
    
    # Redis/Upstash
    REDIS_URL: str = "redis://localhost:6379"
    
    # LLM APIs (Multi-provider with priority order)
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    EURON_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # LLM Fallback Configuration
    LLM_PROVIDERS: List[str] = ["groq", "google", "euron", "openrouter", "mistral"]
    LLM_DEFAULT_MODEL: dict = {
        "groq": "llama-3.3-70b-versatile",
        "google": "gemini-2.0-flash-exp",
        "euron": "gpt-4.1-nano",
        "openrouter": "meta-llama/llama-3.1-8b-instruct:free",
        "mistral": "mistral-small-latest"
    }
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_PROVIDER: str = "local"  # local, openai, cohere
    EMBEDDING_DIMENSIONS: int = 384
    
    # Transcription
    WHISPER_API_KEY: Optional[str] = None
    WHISPER_MODEL: str = "base"  # tiny, base, small, medium, large
    USE_WHISPER_API: bool = True
    
    # OCR
    TESSERACT_PATH: str = "/usr/bin/tesseract"
    
    # Feature Flags
    ENABLE_AUTO_TRANSCRIPTION: bool = True
    ENABLE_AUTO_OCR: bool = True
    ENABLE_AUTO_TAGGING: bool = True
    ENABLE_DUPLICATE_DETECTION: bool = True
    MAX_FILE_SIZE_MB: int = 50
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "chrome-extension://*",
        "https://pinnacle-eight-flax.vercel.app",
        "https://*.vercel.app"
    ]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Queue Configuration
    QUEUE_EXTRACTION: str = "content-extraction"
    QUEUE_EMBEDDING: str = "embedding-generation"
    QUEUE_TRANSCRIPTION: str = "transcription"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# LLM Configuration with API endpoints
LLM_CONFIG = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "max_tokens": 8000,
        "rate_limit": 14400  # per day
    },
    "google": {
        "base_url": None,  # Uses google-generativeai library
        "api_key_env": "GOOGLE_API_KEY",
        "models": ["gemini-2.0-flash-exp", "gemini-1.5-pro"],
        "max_tokens": 8192,
        "rate_limit": 60000  # per minute
    },
    "euron": {
        "base_url": "https://api.euron.one/api/v1/euri",
        "api_key_env": "EURON_API_KEY",
        "models": ["gpt-4.1-nano", "gpt-4o-mini"],
        "max_tokens": 4096,
        "rate_limit": 10000
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "models": [
            "meta-llama/llama-3.1-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free"
        ],
        "max_tokens": 4096,
        "rate_limit": 200
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "models": ["mistral-small-latest", "mistral-tiny"],
        "max_tokens": 8000,
        "rate_limit": 1000000000  # 1B tokens/month
    }
}