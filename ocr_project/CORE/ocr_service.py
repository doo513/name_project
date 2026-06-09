from typing import List, Optional

try:
    import numpy as np
except ImportError:
    np = None

from CORE.ocr_engine import create_ocr_engine


def clean_ocr_text(lines: List[str]) -> List[str]:
    if not lines:
        return lines

    cleaned = []

    for line in lines:
        if not line:
            continue
        line = line.strip()
        if not line:
            continue

        if cleaned:
            prev_line = cleaned[-1]
            if prev_line and (prev_line[-1].isalnum() or line[0].isalnum()):
                char_before = prev_line[-1] if prev_line else ""
                char_after = line[0] if line else ""

                should_merge = False
                if char_before.isalnum() and char_after.isalnum():
                    should_merge = True
                elif char_before.isalnum() and char_after in "'\"":
                    should_merge = True
                elif char_before in "'\"" and char_after.isalnum():
                    should_merge = True

                if should_merge:
                    cleaned[-1] = prev_line + " " + line
                    continue

        cleaned.append(line)

    while cleaned and not cleaned[-1]:
        cleaned.pop()

    return cleaned


class OCRService:
    def __init__(self) -> None:
        self.languages = ["ko", "en"]
        self.engine = create_ocr_engine(self.languages)
        self.last_error: Optional[str] = None

    def set_languages(self, languages: List[str]) -> None:
        normalized = []
        for lang in languages:
            if lang and lang not in normalized:
                normalized.append(lang)

        if not normalized:
            normalized = ["ko", "en"]

        if normalized == self.languages and self.engine is not None:
            return

        self.languages = normalized
        self.engine = create_ocr_engine(self.languages)
        self.last_error = None

    def _engine_error(self) -> str:
        if self.engine is not None and hasattr(self.engine, "get_last_error"):
            err = self.engine.get_last_error()
            if err:
                return err
        if self.last_error:
            return self.last_error
        return f"OCR engine failed to initialize for languages: {self.languages}"

    def is_available(self) -> bool:
        if np is None:
            self.last_error = "numpy is not installed. Install it with: pip install numpy"
            return False
        if self.engine is None:
            self.last_error = "EasyOCR is not installed. Install it with: pip install easyocr"
            return False
        available = self.engine.is_available()
        if not available:
            self.last_error = self._engine_error()
        return available

    def recognize_image_raw(self, image) -> List[str]:
        if self.engine is None:
            raise RuntimeError("EasyOCR is not installed. Install it with: pip install easyocr")
        if np is None:
            raise RuntimeError("numpy is not installed. Install it with: pip install numpy")

        if not self.engine.is_available():
            raise RuntimeError(self._engine_error())

        image_array = np.array(image)
        return self.engine.read_text_simple(image_array)

    def recognize_image(self, image) -> List[str]:
        result = self.recognize_image_raw(image)
        if not result and self.engine is not None and hasattr(self.engine, "get_last_error"):
            err = self.engine.get_last_error()
            if err:
                raise RuntimeError(err)
        return clean_ocr_text([line for line in result if line])
