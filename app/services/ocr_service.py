from typing import Optional
from loguru import logger
import httpx
from PIL import Image
from io import BytesIO
import pytesseract

from app.config import settings

class OCRService:
    """Image OCR service using Tesseract"""
    
    def __init__(self):
        if settings.TESSERACT_PATH:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
    
    async def extract_from_url(self, image_url: str) -> str:
        """Extract text from image URL"""
        try:
            # Download image
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(image_url)
                image_data = response.content
            
            # Open with PIL
            image = Image.open(BytesIO(image_data))
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed for {image_url}: {e}")
            raise
    
    async def extract_from_file(self, file_path: str) -> str:
        """Extract text from local image file"""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {e}")
            raise
    
    async def extract_from_bytes(self, image_bytes: bytes) -> str:
        """Extract text from image bytes"""
        try:
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise

ocr_service = OCRService()