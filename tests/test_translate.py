import unittest
from types import SimpleNamespace
from unittest.mock import patch

from yt_mcp.translate import (
    ArgosTranslateBackend,
    TranslationBackendUnavailableError,
    TranslationLanguageUnavailableError,
)


class ArgosTranslateBackendTests(unittest.TestCase):
    def setUp(self):
        self.backend = ArgosTranslateBackend()
        self.source = SimpleNamespace(code="es")
        self.target = SimpleNamespace(code="en")

    def test_translate_uses_installed_model(self):
        model = SimpleNamespace(translate=lambda text: f"translated: {text}")
        self.source.get_translation = lambda target: model
        argos = SimpleNamespace(get_installed_languages=lambda: [self.source, self.target])

        with patch("yt_mcp.translate._load_argos_translate", return_value=argos):
            result = self.backend.translate("hola", "ES")

        self.assertEqual(result.translated_text, "translated: hola")
        self.assertEqual(result.source_language, "es")
        self.assertEqual(result.target_language, "en")

    def test_translate_errors_when_model_is_missing(self):
        self.source.get_translation = lambda target: None
        argos = SimpleNamespace(get_installed_languages=lambda: [self.source, self.target])

        with patch("yt_mcp.translate._load_argos_translate", return_value=argos):
            with self.assertRaises(TranslationLanguageUnavailableError):
                self.backend.translate("hola", "es")

    def test_availability_is_false_when_argos_is_not_installed(self):
        with patch(
            "yt_mcp.translate._load_argos_translate",
            side_effect=TranslationBackendUnavailableError,
        ):
            self.assertFalse(self.backend.is_available())


if __name__ == "__main__":
    unittest.main()
