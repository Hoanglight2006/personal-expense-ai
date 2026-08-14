from app.config import settings
from app.core.ocr.base import OcrProvider


def get_ocr_provider() -> OcrProvider | None:
    """Factory to get the configured OCR provider."""
    if settings.OCR_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        from app.core.ocr.gemini_provider import GeminiOcrProvider
        return GeminiOcrProvider()
    elif settings.OCR_PROVIDER == "local":
        from app.core.ocr.local_provider import LocalOcrProvider
        return LocalOcrProvider()
    return None
