import unittest
from unittest.mock import patch

from fastapi import HTTPException

from yt_mcp.api import get_transcript, health, translate_video
from yt_mcp.transcript import (
    TooManyRequestsError,
    TranscriptResult,
)
from yt_mcp.translate import TranslationResult


class FastApiBackendTests(unittest.TestCase):
    def setUp(self):
        self.transcript = TranscriptResult(
            video_id="abcdefghijk",
            text="hola mundo",
            segments=[],
            detected_language="es",
            paragraphs=["hola mundo"],
        )

    def test_health_reports_translation_availability(self):
        with patch("yt_mcp.api.translation_backend.is_available", return_value=False):
            self.assertFalse(health()["translation_available"])

    def test_transcript_endpoint_returns_serializable_transcript(self):
        with patch("yt_mcp.api.fetch_transcript", return_value=self.transcript):
            result = get_transcript(
                url="https://youtu.be/abcdefghijk",
                source_language="auto",
            )

        self.assertEqual(result["video_id"], "abcdefghijk")
        self.assertEqual(result["text"], "hola mundo")

    def test_translate_endpoint_uses_detected_source_language(self):
        translated = TranslationResult("hello world", "es", "en", "Argos Translate")
        with patch(
            "yt_mcp.api.fetch_transcript",
            return_value=self.transcript,
        ), patch(
            "yt_mcp.api.translation_backend.translate",
            return_value=translated,
        ) as translate:
            result = translate_video(
                url="https://youtu.be/abcdefghijk",
                source_language="auto",
                target_language="en",
            )

        translate.assert_called_once_with(
            "hola mundo",
            source_lang="es",
            target_lang="en",
        )
        self.assertEqual(result["translated_transcript"], "hello world")
        self.assertEqual(result["translation_chunks"], 1)

    def test_transcript_rate_limit_maps_to_http_429(self):
        with patch(
            "yt_mcp.api.fetch_transcript",
            side_effect=TooManyRequestsError("rate limited"),
        ):
            with self.assertRaises(HTTPException) as raised:
                get_transcript(
                    url="https://youtu.be/abcdefghijk",
                    source_language="auto",
                )

        self.assertEqual(raised.exception.status_code, 429)

    def test_invalid_video_url_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            get_transcript(url="https://example.com/video", source_language="auto")

        self.assertEqual(raised.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
