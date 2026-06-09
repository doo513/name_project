from dataclasses import dataclass
from statistics import median
from typing import List, Sequence, Tuple

try:
    import numpy as np
except ImportError:
    np = None

from CORE.ocr_engine import create_ocr_engine


@dataclass
class OCRToken:
    left: float
    top: float
    right: float
    bottom: float
    text: str
    confidence: float

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.bottom - self.top)


@dataclass(frozen=True)
class OCRPreparedText:
    lines: List[str]
    display_text: str
    translation_text: str


def _contains_cjk(character: str) -> bool:
    if not character:
        return False
    code = ord(character)
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3400 <= code <= 0x4DBF
        or 0x3040 <= code <= 0x30FF
        or 0xAC00 <= code <= 0xD7AF
    )


def _normalize_box(box: Sequence[Sequence[float]]) -> Tuple[float, float, float, float]:
    points = [tuple(point) for point in box if len(point) >= 2]
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _token_from_result(item) -> OCRToken | None:
    if not isinstance(item, (list, tuple)) or len(item) < 3:
        return None

    box, text, confidence = item[0], item[1], item[2]
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return None

    try:
        left, top, right, bottom = _normalize_box(box)
        score = float(confidence)
    except (TypeError, ValueError):
        return None

    return OCRToken(left, top, right, bottom, normalized_text, score)


def _needs_space(previous: str, current: str) -> bool:
    if not previous or not current:
        return False

    prev_char = previous[-1]
    curr_char = current[0]

    if curr_char in ".,!?;:%)]}>»』】、。，！？；：":
        return False
    if prev_char in "([{<«『【":
        return False
    if _contains_cjk(prev_char) and _contains_cjk(curr_char):
        return False
    return True


def _join_token_texts(tokens: List[OCRToken]) -> str:
    parts: List[str] = []
    for token in sorted(tokens, key=lambda item: (item.left, item.top)):
        if not parts:
            parts.append(token.text)
            continue
        if _needs_space(parts[-1], token.text):
            parts.append(" ")
        parts.append(token.text)
    return "".join(parts).strip()


def reconstruct_lines_from_raw(results, confidence_threshold: float = 0.2) -> List[str]:
    tokens = []
    for item in results:
        token = _token_from_result(item)
        if token is None or token.confidence < confidence_threshold:
            continue
        tokens.append(token)

    if not tokens:
        return []

    tokens.sort(key=lambda item: (item.center_y, item.left))
    heights = [token.height for token in tokens]
    y_threshold = max(12.0, median(heights) * 0.65)

    grouped_lines: List[List[OCRToken]] = []
    line_centers: List[float] = []

    for token in tokens:
        best_index = None
        best_distance = None
        for index, center in enumerate(line_centers):
            distance = abs(token.center_y - center)
            if distance <= y_threshold and (best_distance is None or distance < best_distance):
                best_index = index
                best_distance = distance

        if best_index is None:
            grouped_lines.append([token])
            line_centers.append(token.center_y)
            continue

        grouped_lines[best_index].append(token)
        line_centers[best_index] = sum(item.center_y for item in grouped_lines[best_index]) / len(grouped_lines[best_index])

    ordered_pairs = sorted(zip(line_centers, grouped_lines), key=lambda pair: pair[0])
    return [_join_token_texts(line_tokens) for _, line_tokens in ordered_pairs if line_tokens]


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

        cleaned.append(line)

    while cleaned and not cleaned[-1]:
        cleaned.pop()

    return cleaned


def build_display_text(lines: List[str]) -> str:
    cleaned = clean_ocr_text(lines)
    return "\n".join(cleaned).strip()


def build_translation_text(lines: List[str]) -> str:
    cleaned = clean_ocr_text(lines)
    return "\n".join(cleaned).strip()


def prepare_ocr_text(lines: List[str]) -> OCRPreparedText:
    cleaned = clean_ocr_text(lines)
    return OCRPreparedText(
        lines=cleaned,
        display_text=build_display_text(cleaned),
        translation_text=build_translation_text(cleaned),
    )


class OCRService:
    def __init__(self) -> None:
        self.languages = ["ko", "en"]
        self.engine = create_ocr_engine(self.languages)

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

    def is_available(self) -> bool:
        return self.engine is not None and np is not None and self.engine.is_available()

    def recognize_image_raw(self, image):
        if self.engine is None:
            raise RuntimeError("OCR engine is not available.")
        if np is None:
            raise RuntimeError("numpy is not installed.")

        if not self.engine.is_available():
            raise RuntimeError("OCR engine failed to initialize for the selected language pair.")

        image_array = np.array(image)
        return self.engine.read_text_detailed(image_array)

    def recognize_image(self, image) -> OCRPreparedText:
        raw_result = self.recognize_image_raw(image)
        lines = reconstruct_lines_from_raw(raw_result)
        return prepare_ocr_text(lines)
