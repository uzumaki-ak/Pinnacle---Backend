from supabase import create_client
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from loguru import logger

from app.config import settings

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

def normalize_url(url: str) -> str:
    """
    Normalize URL to detect duplicates
    - Remove tracking parameters
    - Normalize YouTube URLs
    - Remove fragments
    - Lowercase domain
    """
    parsed = urlparse(url)
    
    # Lowercase domain
    domain = parsed.netloc.lower()
    
    # Remove common tracking parameters
    tracking_params = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'ref', 'source', '_ga', 'mc_cid', 'mc_eid'
    ]
    
    # Parse query parameters
    query_params = parse_qs(parsed.query)
    filtered_params = {
        k: v for k, v in query_params.items()
        if k not in tracking_params
    }
    
    # Special handling for YouTube
    if 'youtube.com' in domain or 'youtu.be' in domain:
        # Extract video ID
        if 'youtube.com' in domain:
            video_id = query_params.get('v', [None])[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        elif 'youtu.be' in domain:
            video_id = parsed.path.strip('/')
            return f"https://www.youtube.com/watch?v={video_id}"
    
    # Rebuild URL without tracking params and fragment
    new_query = urlencode(filtered_params, doseq=True)
    normalized = urlunparse((
        parsed.scheme,
        domain,
        parsed.path,
        parsed.params,
        new_query,
        ''  # Remove fragment
    ))
    
    return normalized

async def check_duplicate(user_id: str, url: str) -> Optional[Dict[str, Any]]:
    """
    Check if URL already exists for user
    
    Returns:
        Existing item dict if duplicate found, None otherwise
    """
    try:
        # Normalize URL
        normalized_url = normalize_url(url)
        
        # Check if exact match exists
        exact_match = supabase.table("items")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("url", url)\
            .execute()
        
        if exact_match.data:
            return exact_match.data[0]
        
        # Check if normalized URL exists
        if normalized_url != url:
            normalized_match = supabase.table("items")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("url", normalized_url)\
                .execute()
            
            if normalized_match.data:
                return normalized_match.data[0]
        
        return None
        
    except Exception as e:
        logger.error(f"Duplicate check failed: {e}")
        return None