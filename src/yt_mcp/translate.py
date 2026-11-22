"""Offline translation backend for yt-mcp, powered by Argos Translate.

Install the required Argos language packages in the deployment image; this
module intentionally does not download models at runtime.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import ModuleType


@dataclass
class TranslationResult:
    """Result of a translation operation."""

    translated_text: str
    source_language: str
    target_language: str
    model_used: str


class TranslationError(RuntimeError):
    """Base error for translation failures."""


class TranslationBackendUnavailableError(TranslationError):
    """Argos Translate is not installed."""


class TranslationLanguageUnavailableError(TranslationError):
    """No installed Argos model can translate the requested languages."""


class TranslationBackend(ABC):
    """Abstract base class for translation backends."""

    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str = "en",
    ) -> TranslationResult:
        """Translate text from source to target language."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend has at least one installed language model."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the backend."""


class ArgosTranslateBackend(TranslationBackend):
    """Translate locally with installed Argos Translate language packages."""

    @property
    def name(self) -> str:
        return "Argos Translate"

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str = "en",
    ) -> TranslationResult:
        source_code = source_lang.strip().lower()
        target_code = target_lang.strip().lower()
        if not source_code or source_code == "auto":
            raise ValueError("Argos Translate requires a known source language code")
        if not target_code:
            raise ValueError("target_lang must be a language code")

        if not text or source_code == target_code:
            return TranslationResult(text, source_code, target_code, self.name)

        argos_translate = _load_argos_translate()
        languages = argos_translate.get_installed_languages()
        source = next((lang for lang in languages if lang.code == source_code), None)
        target = next((lang for lang in languages if lang.code == target_code), None)
        translation = source.get_translation(target) if source and target else None
        if translation is None:
            raise TranslationLanguageUnavailableError(
                f"No installed Argos Translate model supports "
                f"{source_code} to {target_code}"
            )

        return TranslationResult(
            translated_text=translation.translate(text),
            source_language=source_code,
            target_language=target_code,
            model_used=self.name,
        )

    def is_available(self) -> bool:
        try:
            return bool(_load_argos_translate().get_installed_languages())
        except TranslationBackendUnavailableError:
            return False


def _load_argos_translate() -> ModuleType:
    try:
        import argostranslate.translate as argos_translate
    except ImportError as exc:
        raise TranslationBackendUnavailableError(
            "Argos Translate is not installed; install the python-snap requirements"
        ) from exc
    return argos_translate
