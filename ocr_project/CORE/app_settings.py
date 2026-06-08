import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict


SETTINGS_DIR = Path.home() / ".ocr_study_app"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"


@dataclass
class AppSettings:
    ocr_recheck_count: int = 2
    ocr_hold_seconds: float = 2.0
    ocr_similarity_threshold: float = 0.92
    gemini_api_key: str = ""

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key.strip())


def _coerce_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _coerce_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def load_settings() -> AppSettings:
    if not SETTINGS_PATH.exists():
        return AppSettings()

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppSettings()

    return AppSettings(
        ocr_recheck_count=_coerce_int(data.get("ocr_recheck_count"), 2, 1, 5),
        ocr_hold_seconds=_coerce_float(data.get("ocr_hold_seconds"), 2.0, 0.5, 10.0),
        ocr_similarity_threshold=_coerce_float(data.get("ocr_similarity_threshold"), 0.92, 0.5, 1.0),
        gemini_api_key=str(data.get("gemini_api_key") or "").strip(),
    )


def save_settings(settings: AppSettings) -> None:
    normalized = AppSettings(
        ocr_recheck_count=_coerce_int(settings.ocr_recheck_count, 2, 1, 5),
        ocr_hold_seconds=_coerce_float(settings.ocr_hold_seconds, 2.0, 0.5, 10.0),
        ocr_similarity_threshold=_coerce_float(settings.ocr_similarity_threshold, 0.92, 0.5, 1.0),
        gemini_api_key=settings.gemini_api_key.strip(),
    )
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(asdict(normalized), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        SETTINGS_PATH.chmod(0o600)
    except OSError:
        pass


def settings_status() -> Dict[str, Any]:
    settings = load_settings()
    return {
        "settings_path": str(SETTINGS_PATH),
        "gemini_enabled": settings.gemini_enabled,
        "ocr_recheck_count": settings.ocr_recheck_count,
        "ocr_hold_seconds": settings.ocr_hold_seconds,
        "ocr_similarity_threshold": settings.ocr_similarity_threshold,
    }
