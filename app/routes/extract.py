from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from loguru import logger

from app.routes.auth import get_current_user
from app.services.extraction_service import extraction_service
from app.services.transcription_service import transcription_service
from app.services.ocr_service import ocr_service

router = APIRouter()

class ExtractRequest(BaseModel):
    url: HttpUrl
    extract_transcript: bool = False
    extract_ocr: bool = False

class ExtractResponse(BaseModel):
    title: str
    content: str
    description: Optional[str]
    metadata: Dict[str, Any]

@router.post("/content", response_model=ExtractResponse)
async def extract_content(
    request: ExtractRequest,
    current_user: dict = Depends(get_current_user)
):
    """Extract content from URL"""
    try:
        result = await extraction_service.extract_content(str(request.url))
        
        return ExtractResponse(
            title=result.get("title", ""),
            content=result.get("content", ""),
            description=result.get("description"),
            metadata=result
        )
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transcript")
async def extract_transcript(
    video_url: str,
    current_user: dict = Depends(get_current_user)
):
    """Extract transcript from video/audio URL"""
    try:
        result = await transcription_service.transcribe_url(video_url)
        return result
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ocr")
async def extract_text_from_image(
    image_url: str,
    current_user: dict = Depends(get_current_user)
):
    """Extract text from image URL using OCR"""
    try:
        text = await ocr_service.extract_from_url(image_url)
        return {"text": text, "source": image_url}
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))