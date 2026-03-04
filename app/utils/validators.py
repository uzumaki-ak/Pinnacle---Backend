from urllib.parse import urlparse
import validators as v

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    return v.url(url)

def is_youtube_url(url: str) -> bool:
    """Check if URL is YouTube"""
    parsed = urlparse(url)
    return "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc

def is_image_url(url: str) -> bool:
    """Check if URL points to an image"""
    return url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'))

def is_video_url(url: str) -> bool:
    """Check if URL points to a video"""
    return url.lower().endswith(('.mp4', '.webm', '.ogg', '.mov', '.avi'))

def is_audio_url(url: str) -> bool:
    """Check if URL points to audio"""
    return url.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a', '.flac'))

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for storage"""
    import re
    filename = re.sub(r'[^\w\s.-]', '', filename)
    return filename.strip()