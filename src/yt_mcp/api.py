"""FastAPI HTTP backend for YouTube transcripts and Argos translations."""
from dataclasses import asdict
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Query

from yt_mcp.transcript import (
    NoTranscriptAvailableError,
    TooManyRequestsError,
    TranscriptDisabledError,
    TranscriptResult,
    VideoUnavailableError,
    YouTubeTranscriptError,
    extract_video_id,
    fetch_transcript,
    normalize_language_code,
)
from yt_mcp.translate import (
    ArgosTranslateBackend,
    TranslationBackendUnavailableError,
    TranslationLanguageUnavailableError,
)

app = FastAPI(
    title="YouTube Transcript API",
    description="Fetch YouTube captions and translate them with Argos Translate.",
    version="1.0.0",
)
translation_backend = ArgosTranslateBackend()
_WORDS_PER_CHUNK = 500


@app.get("/health")
def health() -> Dict[str, object]:
    """Report server and local translation-model availability."""
    return {
        "service": "youtube-transcript-translator",
        "status": "ok",
        "translation_available": translation_backend.is_available(),
    }


@app.get("/transcript")
def get_transcript(
    url: str = Query(..., description="YouTube URL or 11-character video ID"),
    source_language: str = Query("auto", description="Preferred transcript language"),
) -> Dict[str, object]:
    """Fetch a video's transcript and timing segments."""
    transcript = _fetch_transcript(url, source_language)
    return asdict(transcript)


@app.get("/translate")
def translate_video(
    url: str = Query(..., description="YouTube URL or 11-character video ID"),
    source_language: str = Query("auto", description="Preferred transcript language"),
    target_language: str = Query("en", description="Translation target language"),
) -> Dict[str, object]:
    """Fetch a transcript and translate it using installed Argos models."""
    transcript = _fetch_transcript(url, source_language)
    detected_language = normalize_language_code(transcript.detected_language)
    requested_language = normalize_language_code(source_language)
    source_code = (
        detected_language if detected_language != "auto" else requested_language
    )
    target_code = normalize_language_code(target_language)

    translated_chunks: List[str] = []
    try:
        for chunk in _split_text(transcript.text):
            translated = translation_backend.translate(
                chunk,
                source_lang=source_code,
                target_lang=target_code,
            )
            translated_chunks.append(translated.translated_text)
    except TranslationBackendUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TranslationLanguageUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "video_id": transcript.video_id,
        "original_transcript": transcript.text,
        "source_language": source_code,
        "translated_to": target_code,
        "translated_transcript": "\n\n".join(translated_chunks),
        "translation_chunks": len(translated_chunks),
    }


def _fetch_transcript(url: str, source_language: str) -> TranscriptResult:
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=422, detail="Invalid YouTube URL or video ID")

    try:
        return fetch_transcript(video_id, preferred_language=source_language)
    except TooManyRequestsError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except (
        NoTranscriptAvailableError,
        TranscriptDisabledError,
        VideoUnavailableError,
    ) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except YouTubeTranscriptError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _split_text(text: str) -> List[str]:
    words = text.split()
    return [
        " ".join(words[index : index + _WORDS_PER_CHUNK])
        for index in range(0, len(words), _WORDS_PER_CHUNK)
    ]
