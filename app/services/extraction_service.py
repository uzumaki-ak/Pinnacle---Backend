import trafilatura
from newspaper import Article
from bs4 import BeautifulSoup
import httpx
from typing import Optional, Dict, Any
from loguru import logger
from urllib.parse import urlparse
import re

from app.utils.youtube import extract_youtube_transcript
from app.services.llm_service import llm_service

class ExtractionService:
    """Service for extracting content from URLs"""
    
    def __init__(self):
        self.timeout = 30
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    async def extract_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a URL with appropriate method based on domain
        
        Returns dict with title, content, description, author, date, etc.
        """
        try:
            # Detect media type from URL
            domain = urlparse(url).netloc.lower()
            
            # YouTube videos
            if "youtube.com" in domain or "youtu.be" in domain:
                return await self.extract_youtube(url)
            
            # Twitter/X
            elif "twitter.com" in domain or "x.com" in domain:
                return await self.extract_twitter(url)
            
            # Instagram
            elif "instagram.com" in domain:
                return await self.extract_instagram(url)
            
            # Generic article/webpage
            else:
                return await self.extract_article(url)
                
        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {e}")
            return {
                "title": url,
                "content": "",
                "description": "",
                "error": str(e)
            }
    
    async def extract_article(self, url: str) -> Dict[str, Any]:
        """Extract article content using trafilatura + newspaper3k"""
        try:
            # First try trafilatura (faster, better for articles)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers={"User-Agent": self.user_agent})
                html = response.text
            
            # Extract with trafilatura
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(html)
            
            # Fallback to newspaper3k for better title/description
            article = Article(url)
            article.download(input_html=html)
            article.parse()
            
            return {
                "title": metadata.title or article.title or url,
                "content": content or article.text,
                "description": metadata.description or article.meta_description,
                "author": metadata.author or ", ".join(article.authors) if article.authors else None,
                "published_date": metadata.date or article.publish_date,
                "image": article.top_image,
                "domain": urlparse(url).netloc,
                "word_count": len(content.split()) if content else 0
            }
            
        except Exception as e:
            logger.error(f"Article extraction failed: {e}")
            raise
    
    async def extract_youtube(self, url: str) -> Dict[str, Any]:
        """Extract YouTube video metadata and transcript"""
        try:
            # Extract video ID
            video_id = self._extract_youtube_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
            
            # Get transcript
            transcript_data = await extract_youtube_transcript(video_id)
            
            # Fetch video metadata from oEmbed
            metadata = {}
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(
                        f"https://www.youtube.com/oembed?url={url}&format=json"
                    )
                    metadata = response.json()
            except:
                pass
            
            # Use transcript content or fallback to description
            content = transcript_data.get("transcript", "")
            
            # If no content from transcript, try LLM to generate summary
            if not content:
                logger.warning("No transcript available, using LLM to generate content...")
                try:
                    title = metadata.get("title", "YouTube Video")
                    llm_response = await llm_service.chat_completion(
                        messages=[{
                            "role": "user",
                            "content": f"Based on the title '{title}', generate a brief description of what this video likely contains. Keep it under 200 words."
                        }],
                        temperature=0.5,
                        max_tokens=200
                    )
                    content = llm_response.get("content", "")
                    logger.info(f"Generated content via LLM for {video_id}")
                except Exception as llm_error:
                    logger.warning(f"LLM fallback failed: {llm_error}")
            
            return {
                "title": metadata.get("title", "YouTube Video"),
                "content": content,
                "description": "",
                "author": metadata.get("author_name", ""),
                "thumbnail": metadata.get("thumbnail_url", ""),
                "video_id": video_id,
                "duration": transcript_data.get("duration"),
                "media_type": "youtube",
                "source": transcript_data.get("source", "unknown")
            }
            
        except Exception as e:
            logger.error(f"YouTube extraction failed: {e}")
            raise
    
    async def extract_twitter(self, url: str) -> Dict[str, Any]:
        """Extract Twitter/X post content"""
        try:
            # For Twitter, we'll extract basic info from HTML
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers={"User-Agent": self.user_agent})
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract tweet text from meta tags
            description = soup.find("meta", property="og:description")
            title = soup.find("meta", property="og:title")
            image = soup.find("meta", property="og:image")
            
            return {
                "title": title["content"] if title else "Twitter Post",
                "content": description["content"] if description else "",
                "description": "",
                "image": image["content"] if image else None,
                "media_type": "twitter"
            }
            
        except Exception as e:
            logger.error(f"Twitter extraction failed: {e}")
            raise
    
    async def extract_instagram(self, url: str) -> Dict[str, Any]:
        """Extract Instagram post metadata"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": self.user_agent},
                    follow_redirects=True
                )
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract from meta tags
            description = soup.find("meta", property="og:description")
            image = soup.find("meta", property="og:image")
            title = soup.find("meta", property="og:title")
            
            return {
                "title": title["content"] if title else "Instagram Post",
                "content": description["content"] if description else "",
                "description": "",
                "image": image["content"] if image else None,
                "media_type": "instagram"
            }
            
        except Exception as e:
            logger.error(f"Instagram extraction failed: {e}")
            raise
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def extract_favicon(self, url: str) -> Optional[str]:
        """Extract favicon URL from website"""
        try:
            domain = urlparse(url).netloc
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
        except:
            return None

# Global instance
extraction_service = ExtractionService()