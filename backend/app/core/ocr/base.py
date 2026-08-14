from abc import ABC, abstractmethod
from decimal import Decimal
from typing import NamedTuple

from app.models.enums import CategoryType, PaymentMethod


class ExtractedTransaction(NamedTuple):
    """Data extracted from an image via OCR."""
    amount: Decimal | None
    transaction_date: str | None
    description: str | None
    type_suggestion: CategoryType | None
    payment_method_suggestion: PaymentMethod | None
    category_id: int | None


class OcrProvider(ABC):
    """Abstract base class for OCR extraction."""

    @abstractmethod
    def extract_transaction(self, image_bytes: bytes, categories: list | None = None) -> ExtractedTransaction:
        """Extract transaction information from an image.
        Categories parameter can be passed to help AI infer the best matching category.
        """
        pass
