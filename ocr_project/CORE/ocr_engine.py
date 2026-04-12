import logging
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import easyocr
except ImportError:
    easyocr = None


logger = logging.getLogger(__name__)

# Module-level shared OCREngine instance
_shared_engine: Optional['OCREngine'] = None


def get_ocr_engine() -> Optional['OCREngine']:
    """
    Get the shared OCREngine instance.
    Creates it on first call, then reuses the same instance.
    
    Returns:
        Shared OCREngine instance, or None if OCREngine is not available.
    
    Example:
        >>> engine = get_ocr_engine()
        >>> if engine:
        ...     result = engine.read_text('image.jpg')
    """
    global _shared_engine
    if _shared_engine is None and easyocr is not None:
        _shared_engine = OCREngine()
    return _shared_engine


class OCREngine:
    """
    OCR engine wrapper using EasyOCR for multi-language text extraction.
    
    Supports multiple languages: English, Russian, Arabic, Korean.
    Uses lazy initialization to avoid loading the model until first use.
    """

    def __init__(self, languages: Optional[List[str]] = None) -> None:
        """
        Initialize OCREngine with specified languages.
        
        Args:
            languages: List of language codes (e.g., ['en', 'ru', 'ar', 'ko']).
                      Defaults to ['en', 'ru', 'ar', 'ko'] if not provided.
        """
        self.languages = languages or ['ko', 'en']
        self._reader: Optional[object] = None

    def _ensure_reader(self) -> bool:
        """
        Lazy initialize the EasyOCR reader on first use.
        
        Returns:
            True if reader is available, False otherwise.
        """
        if self._reader is not None:
            return True

        if easyocr is None:
            logger.error("EasyOCR is not installed")
            return False

        try:
            self._reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR reader: {e}")
            return False

    def is_available(self) -> bool:
        """
        Check if OCR engine is available and working.
        
        Returns:
            True if OCR is available, False otherwise.
        """
        return self._ensure_reader()

    def read_text(self, image_path: str) -> List[Tuple[str, float]]:
        """
        Extract text from image with confidence scores.
        
        Args:
            image_path: Path to the image file.
        
        Returns:
            List of tuples: [(text, confidence), ...].
            Returns empty list on error.
        
        Example:
            >>> engine = OCREngine()
            >>> result = engine.read_text('image.jpg')
            >>> print(result)
            [('Hello world', 0.95), ('Привет', 0.88)]
        """
        if not self._ensure_reader():
            return []

        try:
            image_path = Path(image_path)
            if not image_path.exists():
                logger.warning(f"Image file not found: {image_path}")
                return []

            result = self._reader.readtext(str(image_path))
            
            # EasyOCR returns: [(bbox, text, confidence), ...]
            # Extract text and confidence
            extracted = [(text, float(confidence)) for _, text, confidence in result]
            return extracted

        except Exception as e:
            logger.error(f"Failed to read text from {image_path}: {e}")
            return []

    def read_text_simple(self, image_path: str) -> List[str]:
        """
        Extract text from image (simple format, text only).
        
        Args:
            image_path: Path to the image file OR numpy array image.
        
        Returns:
            List of extracted text strings.
            Returns empty list on error.
        
        Example:
            >>> engine = OCREngine()
            >>> result = engine.read_text_simple('image.jpg')
            >>> print(result)
            ['Hello world', 'Привет', 'مرحبا']
        """
        if not self._ensure_reader():
            return []

        try:
            # Check if it's a numpy array (memory image)
            import numpy as np
            if isinstance(image_path, np.ndarray):
                result = self._reader.readtext(image_path, detail=0)
                return list(result)
            
            # Otherwise treat as file path
            image_path = Path(image_path)
            if not image_path.exists():
                logger.warning(f"Image file not found: {image_path}")
                return []

            result = self._reader.readtext(str(image_path), detail=0)
            
            # EasyOCR with detail=0 returns: ['text1', 'text2', ...]
            return list(result)

        except Exception as e:
            logger.error(f"Failed to read text: {e}")
            return []
