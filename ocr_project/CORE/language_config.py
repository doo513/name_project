from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class LanguageOption:
    name: str
    code: str
    ocr_code: str
    translation_code: str
    use_english_ocr_fallback: bool = True


LANGUAGE_OPTIONS: Tuple[LanguageOption, ...] = (
    LanguageOption("Korean", "ko", "ko", "ko"),
    LanguageOption("English", "en", "en", "en", False),
    LanguageOption("Japanese", "ja", "ja", "ja"),
    LanguageOption("Chinese Simplified", "zh-CN", "ch_sim", "zh-CN"),
    LanguageOption("Chinese Traditional", "zh-TW", "ch_tra", "zh-TW"),
    LanguageOption("Spanish", "es", "es", "es"),
    LanguageOption("French", "fr", "fr", "fr"),
    LanguageOption("German", "de", "de", "de"),
    LanguageOption("Russian", "ru", "ru", "ru"),
    LanguageOption("Arabic", "ar", "ar", "ar"),
)

DEFAULT_SOURCE_LANGUAGE = "en"
DEFAULT_TARGET_LANGUAGE = "ko"

LANGUAGE_CODES: Tuple[str, ...] = tuple(option.code for option in LANGUAGE_OPTIONS)
LANGUAGE_CODE_TO_OPTION: Dict[str, LanguageOption] = {option.code: option for option in LANGUAGE_OPTIONS}
LANGUAGE_CODE_TO_NAME: Dict[str, str] = {option.code: option.name for option in LANGUAGE_OPTIONS}
LANGUAGE_CODE_TO_OCR: Dict[str, str] = {option.code: option.ocr_code for option in LANGUAGE_OPTIONS}
LANGUAGE_CODE_TO_TRANSLATION: Dict[str, str] = {
    option.code: option.translation_code for option in LANGUAGE_OPTIONS
}

# Backward compatibility for old UI/config values.
LANGUAGE_ALIASES: Dict[str, str] = {
    "zh": "zh-CN",
    "ch_sim": "zh-CN",
    "ch_tra": "zh-TW",
}


def normalize_language_code(code: str) -> str:
    if not code:
        return DEFAULT_SOURCE_LANGUAGE
    return LANGUAGE_ALIASES.get(code, code)


def get_language_name(code: str) -> str:
    normalized = normalize_language_code(code)
    return LANGUAGE_CODE_TO_NAME.get(normalized, normalized.upper())


def get_ocr_languages(source_code: str) -> List[str]:
    """Return OCR backend language codes for the selected source language.

    Important: this returns source-language OCR codes only. It does not include the
    translation target language. English is added as an OCR fallback for non-English
    sources because screen text commonly contains numbers, UI labels, acronyms, and
    mixed English text. This keeps OCR stable without mixing in the target language.
    """
    normalized = normalize_language_code(source_code)
    option = LANGUAGE_CODE_TO_OPTION.get(normalized)
    if option is None:
        return [normalized]

    languages = [option.ocr_code]
    if option.use_english_ocr_fallback and option.ocr_code != "en":
        languages.append("en")
    return languages


def get_translation_language(code: str) -> str:
    normalized = normalize_language_code(code)
    return LANGUAGE_CODE_TO_TRANSLATION.get(normalized, normalized)
