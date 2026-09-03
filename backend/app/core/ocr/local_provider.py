import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pytesseract
from PIL import Image
import io

from app.core.ocr.base import ExtractedTransaction, OcrProvider
from app.models.enums import CategoryType, PaymentMethod


class LocalOcrProvider(OcrProvider):
    """Local OCR extraction using pytesseract.
    Requires Tesseract to be installed on the host system.
    """

    def __init__(self):
        try:
            # Check if tesseract is installed
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            raise RuntimeError(
                "OCR engine chưa được cấu hình. "
                "Vui lòng cài đặt Tesseract OCR trên hệ thống."
            )

    def extract_transaction(self, image_bytes: bytes, categories: list | None = None) -> ExtractedTransaction:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Convert to grayscale for better OCR
            img = img.convert("L")
            raw_text = pytesseract.image_to_string(img, lang="vie+eng")
            text: str = raw_text if isinstance(raw_text, str) else str(raw_text)
        except Exception as e:
            raise RuntimeError(f"Lỗi đọc ảnh: {e}")

        # Basic naive regex extraction (can be improved with LLM or better rules)
        amount = self._extract_amount(text)
        date_str = self._extract_date(text)
        
        # Suggestion based on keywords
        text_lower = text.lower()
        type_sugg = CategoryType.EXPENSE
        if any(kw in text_lower for kw in ["nhận", "cộng", "+", "chuyển đến", "lương"]):
            type_sugg = CategoryType.INCOME
        elif any(kw in text_lower for kw in ["trừ", "-", "thanh toán", "chuyển cho"]):
            type_sugg = CategoryType.EXPENSE

        method_sugg = PaymentMethod.CASH
        if any(kw in text_lower for kw in ["chuyển khoản", "nap", "ck", "bank"]):
            method_sugg = PaymentMethod.BANK_TRANSFER

        # First line usually contains the description or title
        desc = text.split("\n")[0][:255] if text else None

        return ExtractedTransaction(
            amount=amount,
            transaction_date=date_str,
            description=desc,
            type_suggestion=type_sugg,
            payment_method_suggestion=method_sugg,
            category_id=None,
        )

    def _extract_amount(self, text: str) -> Decimal | None:
        # Match common currency formats: 100,000, 100.000, 100000 VNĐ
        matches = re.findall(r"(?:VND|VNĐ|\$)?\s*([0-9]{1,3}(?:[,.][0-9]{3})+|[0-9]+)\s*(?:VND|VNĐ)?", text, re.IGNORECASE)
        for match in matches:
            clean_val = re.sub(r"[,.]", "", match)
            try:
                val = Decimal(clean_val)
                if val > 0:
                    return val
            except InvalidOperation:
                continue
        return None

    def _extract_date(self, text: str) -> str | None:
        # Match DD/MM/YYYY or DD-MM-YYYY
        matches = re.findall(r"(\d{2})[/.-](\d{2})[/.-](\d{4})", text)
        for d, m, y in matches:
            try:
                dt = datetime(int(y), int(m), int(d))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
