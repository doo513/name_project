import logging
import textwrap
from typing import Optional

logger = logging.getLogger(__name__)

GoogleTranslator = None

try:
    from deep_translator import GoogleTranslator
except ImportError:
    pass


class TranslationService:
    def __init__(
        self,
        source: str = "en",
        target: str = "ko",
    ) -> None:
        self.source = source
        self.target = target
        self._translator = None

    def _ensure_translator(self):
        if self._translator is None:
            if GoogleTranslator is None:
                raise RuntimeError("deep-translator is not installed.")
            src = self.source if self.source != "auto" else "en"
            self._translator = GoogleTranslator(source=src, target=self.target)

    def set_target_language(self, target: str) -> None:
        self.target = target
        self._translator = None

    def set_source_language(self, source: str) -> None:
        self.source = source
        self._translator = None

    def translate(self, text: str) -> Optional[str]:
        if not text or not text.strip():
            return None

        if GoogleTranslator is None:
            return None

        try:
            self._ensure_translator()
            if len(text) <= 500:
                return self._translator.translate(text)
            else:
                chunks = textwrap.wrap(text, 450, break_long_words=False)
                results = []
                for chunk in chunks:
                    t = GoogleTranslator(
                        source=self.source if self.source != "auto" else "en",
                        target=self.target
                    ).translate(chunk)
                    if t:
                        results.append(t)
                return " ".join(results) if results else None
        except Exception as exc:
            logger.error(f"Translation failed: {exc}")
            return None

    def translate_batch(self, texts: list[str]) -> list[str]:
        if not texts:
            return []
        if GoogleTranslator is None:
            return []
        try:
            self._ensure_translator()
            results = self._translator.translate_batch(texts)
            return list(results)
        except Exception as exc:
            logger.warning(f"Translation batch failed: {exc}")
            return []

    def is_available(self) -> bool:
        return GoogleTranslator is not None


_DEFAULT_SERVICE: Optional["TranslationService"] = None


def get_translation_service(
    source: str = "en",
    target: str = "ko",
) -> "TranslationService":
    global _DEFAULT_SERVICE
    if _DEFAULT_SERVICE is None:
        _DEFAULT_SERVICE = TranslationService(source=source, target=target)
    return _DEFAULT_SERVICE


def translate_text(
    text: str,
    source: str = "en",
    target: str = "ko",
) -> Optional[str]:
    service = get_translation_service(source=source, target=target)
    service.set_target_language(target)
    return service.translate(text)