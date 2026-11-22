"""
YouTube Transcript fetching module using youtube-transcript-api.
"""
import re
from dataclasses import dataclass
from typing import Optional, List
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    RequestBlocked,
    VideoUnavailable,
)


@dataclass
class TranscriptSegment:
    """Represents a single segment of a transcript."""
    text: str
    start: float
    duration: float
    lang: Optional[str] = None


@dataclass
class TranscriptResult:
    """Result of fetching a YouTube transcript."""
    video_id: str
    text: str
    segments: List[TranscriptSegment]
    detected_language: str
    paragraphs: List[str]


# Language code aliases (matching the JS implementation)
LANGUAGE_ALIASES = {
    "auto": "auto",
    "english": "en",
    "en": "en",
    "hindi": "hi",
    "hi": "hi",
    "spanish": "es",
    "es": "es",
    "french": "fr",
    "fr": "fr",
    "german": "de",
    "de": "de",
    "italian": "it",
    "it": "it",
    "portuguese": "pt",
    "pt": "pt",
    "japanese": "ja",
    "ja": "ja",
    "korean": "ko",
    "ko": "ko",
    "chinese": "zh",
    "zh": "zh",
    "arabic": "ar",
    "ar": "ar",
    "russian": "ru",
    "ru": "ru",
    "turkish": "tr",
    "tr": "tr",
    "dutch": "nl",
    "nl": "nl",
    "polish": "pl",
    "pl": "pl",
    "ukrainian": "uk",
    "uk": "uk",
    "swedish": "sv",
    "sv": "sv",
    "vietnamese": "vi",
    "vi": "vi",
    "thai": "th",
    "th": "th",
    "indonesian": "id",
    "id": "id",
    "hebrew": "he",
    "he": "he",
    "norwegian": "no",
    "no": "no",
    "danish": "da",
    "da": "da",
    "finnish": "fi",
    "fi": "fi",
    "greek": "el",
    "el": "el",
    "czech": "cs",
    "cs": "cs",
    "romanian": "ro",
    "ro": "ro",
}


def normalize_language_code(language: Optional[str]) -> str:
    """Normalize language code to standard format."""
    if language is None:
        return "auto"
    
    normalized = str(language).strip().lower()
    
    if not normalized:
        return "auto"
    
    return LANGUAGE_ALIASES.get(normalized, normalized)


def extract_video_id(url_or_id: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats or return the ID if already valid.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - VIDEO_ID (11 characters)
    """
    # If it's already an 11-character video ID, return it
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url_or_id)
        
        # youtu.be/VIDEO_ID
        if parsed.hostname == "youtu.be":
            return parsed.path.lstrip("/").split("/")[0]
        
        # youtube.com, www.youtube.com, m.youtube.com
        if parsed.hostname in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            # /watch?v=VIDEO_ID
            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]
            
            # /live/VIDEO_ID
            if parsed.path.startswith("/live/"):
                return parsed.path.split("/")[2]
            
            # /shorts/VIDEO_ID
            if parsed.path.startswith("/shorts/"):
                return parsed.path.split("/")[2]
            
            # /embed/VIDEO_ID
            if parsed.path.startswith("/embed/"):
                return parsed.path.split("/")[2]
        
        return None
    except Exception:
        return None


class YouTubeTranscriptError(Exception):
    """Base exception for YouTube transcript errors."""
    pass


class TranscriptDisabledError(YouTubeTranscriptError):
    """Transcripts are disabled for this video."""
    pass


class VideoUnavailableError(YouTubeTranscriptError):
    """Video is unavailable."""
    pass


class NoTranscriptAvailableError(YouTubeTranscriptError):
    """No transcript found for the video."""
    pass


class TooManyRequestsError(YouTubeTranscriptError):
    """Rate limited by YouTube."""
    pass


def fetch_transcript(
    video_id: str,
    preferred_language: str = "auto",
) -> TranscriptResult:
    """
    Fetch transcript for a YouTube video.
    
    Args:
        video_id: YouTube video ID (11 characters)
        preferred_language: Preferred language code (e.g., 'en', 'es', 'auto')
    
    Returns:
        TranscriptResult with the transcript data
    
    Raises:
        YouTubeTranscriptError: On various failure conditions
    """
    normalized_lang = normalize_language_code(preferred_language)
    
    try:
        api = YouTubeTranscriptApi()
        
        transcript_list = api.list(video_id)
        if normalized_lang != "auto":
            try:
                transcript = transcript_list.find_transcript([normalized_lang])
            except NoTranscriptFound:
                transcript = next(iter(transcript_list), None)
        else:
            transcript = next(iter(transcript_list), None)

        if transcript is None:
            raise NoTranscriptAvailableError(
                f"No transcript found for video {video_id}"
            )
        fetched = transcript.fetch()
        
        # Convert to our data structures
        detected_lang = getattr(fetched, "language_code", None) or (
            normalized_lang if normalized_lang != "auto" else "en"
        )
        segments = []
        
        for snippet in fetched:
            segment = TranscriptSegment(
                text=snippet.text,
                start=snippet.start,
                duration=snippet.duration,
                lang=(
                    getattr(snippet, "language_code", None)
                    or getattr(snippet, "lang", None)
                    or detected_lang
                ),
            )
            segments.append(segment)
        
        # Build full text
        full_text = " ".join(seg.text for seg in segments)
        
        # Create paragraphs (split by double newlines or long pauses)
        paragraphs = _create_paragraphs(segments)
        
        return TranscriptResult(
            video_id=video_id,
            text=full_text,
            segments=segments,
            detected_language=detected_lang,
            paragraphs=paragraphs,
        )
    
    except TranscriptsDisabled:
        raise TranscriptDisabledError(f"Transcripts are disabled for video {video_id}")
    except VideoUnavailable:
        raise VideoUnavailableError(f"Video {video_id} is unavailable")
    except NoTranscriptFound:
        raise NoTranscriptAvailableError(f"No transcript found for video {video_id}")
    except RequestBlocked:
        raise TooManyRequestsError("Too many requests to YouTube. Please try again later.")
    except Exception as e:
        raise YouTubeTranscriptError(f"Failed to fetch transcript: {str(e)}")


def _create_paragraphs(segments: List[TranscriptSegment], gap_threshold: float = 3.0) -> List[str]:
    """Create paragraphs from segments based on time gaps."""
    if not segments:
        return []
    
    paragraphs = []
    current_paragraph = [segments[0].text]
    
    for i in range(1, len(segments)):
        prev_end = segments[i - 1].start + segments[i - 1].duration
        curr_start = segments[i].start
        gap = curr_start - prev_end
        
        if gap > gap_threshold:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = [segments[i].text]
        else:
            current_paragraph.append(segments[i].text)
    
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))
    
    return paragraphs