from typing import Optional, Dict, Any
from loguru import logger
import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.utils.youtube import extract_youtube_transcript

class TranscriptionService:
    """Audio/Video transcription service using Whisper"""
    
    def __init__(self):
        self.use_api = settings.USE_WHISPER_API and settings.WHISPER_API_KEY
        if self.use_api:
            self.client = AsyncOpenAI(api_key=settings.WHISPER_API_KEY)
    
    async def transcribe_url(self, url: str) -> Dict[str, Any]:
        """Transcribe audio/video from URL"""
        # Check if YouTube
        if "youtube.com" in url or "youtu.be" in url:
            return await self.transcribe_youtube(url)
        
        # For other URLs, download and transcribe
        return await self.transcribe_file_from_url(url)
    
    async def transcribe_youtube(self, url: str) -> Dict[str, Any]:
        """Get YouTube transcript"""
        from urllib.parse import urlparse, parse_qs
        
        # Extract video ID
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc:
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        else:
            video_id = parsed.path.strip("/")
        
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        result = await extract_youtube_transcript(video_id)
        return result
    
    async def transcribe_file_from_url(self, url: str) -> Dict[str, Any]:
        """Download and transcribe audio/video file"""
        if not self.use_api:
            raise Exception("Whisper API not configured. Set WHISPER_API_KEY.")
        
        try:
            # Download file
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.get(url)
                audio_data = response.content
            
            # Transcribe using OpenAI Whisper
            from io import BytesIO
            audio_file = BytesIO(audio_data)
            audio_file.name = "audio.mp3"
            
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            
            return {
                "transcript": transcript.text,
                "language": transcript.language if hasattr(transcript, "language") else None,
                "duration": None
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    async def transcribe_local_file(self, file_path: str) -> str:
        """Transcribe local audio/video file"""
        if not self.use_api:
            # Use local Whisper (requires whisper package)
            import whisper
            model = whisper.load_model(settings.WHISPER_MODEL)
            result = model.transcribe(file_path)
            return result["text"]
        else:
            with open(file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                return transcript.text

transcription_service = TranscriptionService()