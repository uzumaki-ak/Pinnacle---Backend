from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from typing import Optional, Dict, Any
from loguru import logger
import time

async def extract_youtube_transcript(video_id: str) -> Dict[str, Any]:
    """Extract transcript from YouTube video with multiple fallbacks"""
    try:
        # Try main transcript extraction with retry
        for attempt in range(2):
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                try:
                    transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
                except:
                    try:
                        transcript = transcript_list.find_generated_transcript(['en'])
                    except:
                        transcript = None
                
                if transcript:
                    transcript_data = transcript.fetch()
                    full_text = " ".join([entry['text'] for entry in transcript_data])
                    duration = max([entry['start'] + entry['duration'] for entry in transcript_data])
                    
                    return {
                        "transcript": full_text,
                        "duration": duration,
                        "language": transcript.language_code,
                        "is_generated": transcript.is_generated,
                        "timestamps": transcript_data
                    }
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Transcript attempt 1 failed, retrying: {e}")
                    time.sleep(1)
                    continue
                raise
        
    except Exception as e:
        logger.warning(f"YouTube transcript extraction failed: {e}")
    
    # FALLBACK 1: Get video metadata using yt_dlp
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True,
            'socket_timeout': 30
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
            
            description = info.get('description', '') or ''
            title = info.get('title', '') or ''
            duration = info.get('duration')
            
            if description or title:
                return {
                    "transcript": f"{title}. {description}".strip(),
                    "duration": duration,
                    "language": None,
                    "is_generated": False,
                    "source": "metadata_fallback"
                }
    except Exception as e:
        logger.warning(f"yt_dlp fallback failed: {e}")
    
    # FALLBACK 2: Return empty transcript
    logger.error(f"Could not extract any content for video {video_id}")
    return {
        "transcript": "",
        "duration": None,
        "language": None,
        "is_generated": None,
        "source": "empty"
    }
