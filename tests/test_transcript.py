import unittest
from types import SimpleNamespace
from unittest.mock import patch

from yt_mcp.transcript import fetch_transcript


class TranscriptLanguageTests(unittest.TestCase):
    def test_auto_language_uses_youtube_transcript_metadata(self):
        class FetchedTranscript(list):
            language_code = "es"

        fetched = FetchedTranscript(
            [SimpleNamespace(text="hola", start=0, duration=1)]
        )
        transcript = SimpleNamespace(fetch=lambda: fetched)
        transcript_list = [transcript]
        api = SimpleNamespace(list=lambda video_id: transcript_list)

        with patch("yt_mcp.transcript.YouTubeTranscriptApi", return_value=api):
            result = fetch_transcript("abcdefghijk")

        self.assertEqual(result.detected_language, "es")
        self.assertEqual(result.segments[0].lang, "es")


if __name__ == "__main__":
    unittest.main()
