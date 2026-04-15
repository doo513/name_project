import logging
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import easyocr
except ImportError:
    easyocr = None


logger = logging.getLogger(__name__)

_shared_engine: Optional["OCREngine"] = None


def get_ocr_engine() -> Optional["OCREngine"]:
    """
    Get the shared OCR engine instance.

    Creates it on first call, then reuses the same instance.
    """
    global _shared_engine
    if _shared_engine is None and easyocr is not None:
        _shared_engine = OCREngine()
    return _shared_engine


def create_ocr_engine(languages: Optional[List[str]] = None) -> Optional["OCREngine"]:
    if easyocr is None:
        return None
    return OCREngine(languages=languages)


class OCREngine:
    """
    EasyOCR wrapper for screen text extraction.

    The reader is initialized lazily because model loading is expensive.
    """

    def __init__(self, languages: Optional[List[str]] = None) -> None:
        self.languages = languages or ["ko", "en"]
        self._reader: Optional[object] = None

    def _ensure_reader(self) -> bool:
        if self._reader is not None:
            return True

        if easyocr is None:
            logger.error("EasyOCR is not installed")
            return False

        try:
            self._reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
            return True
        except Exception as exc:
            logger.error(f"Failed to initialize EasyOCR reader: {exc}")
            return False

    def is_available(self) -> bool:
        return self._ensure_reader()

    def read_text(self, image_path: str) -> List[Tuple[str, float]]:
        if not self._ensure_reader():
            return []

        try:
            path = Path(image_path)
            if not path.exists():
                logger.warning(f"Image file not found: {path}")
                return []

            result = self._reader.readtext(str(path))
            return [(text, float(confidence)) for _, text, confidence in result]
        except Exception as exc:
            logger.error(f"Failed to read text from {image_path}: {exc}")
            return []

    def read_text_simple(self, image_input) -> List[str]:
        if not self._ensure_reader():
            return []

        try:
            import numpy as np

            if isinstance(image_input, np.ndarray):
                result = self._reader.readtext(image_input, detail=0)
                return list(result)

            path = Path(image_input)
            if not path.exists():
                logger.warning(f"Image file not found: {path}")
                return []

            result = self._reader.readtext(str(path), detail=0)
            return list(result)
        except Exception as exc:
            logger.error(f"Failed to read text: {exc}")
            return []
