import json
import logging
from decimal import Decimal

import google.generativeai as genai
from pydantic import ValidationError

from app.config import settings
from app.core.ocr.base import ExtractedTransaction, OcrProvider
from app.models.enums import CategoryType, PaymentMethod

from app.core.prompts import format_prompt

logger = logging.getLogger(__name__)


class GeminiOcrProvider(OcrProvider):
    """OCR extraction using Google Gemini API."""

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured in .env.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def extract_transaction(self, image_bytes: bytes, categories: list | None = None) -> ExtractedTransaction:
        categories_context = ""
        if categories:
            categories_list = "\n".join([f"- ID {c.id}: {c.name} ({c.type.value if hasattr(c.type, 'value') else c.type})" for c in categories])
            categories_context = f"""
        Available Categories in system:
        {categories_list}
        
        Based on the items/products in the receipt and the store name, choose the MOST LOGICAL category_id from the list above. If you cannot determine it confidently, return null.
        """
        
        prompt = format_prompt("receipt_ocr", "prompt_template", categories_context=categories_context)
        
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": image_bytes
            }
        ]
        
        text = ""
        try:
            response = self.model.generate_content([prompt, image_parts[0]])
            text = response.text
            
            # Clean markdown if present
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()
            
            data = json.loads(text)
            
            # Parse amount
            amount = None
            if data.get("amount") is not None:
                try:
                    amount = Decimal(str(data["amount"]))
                except Exception:
                    pass
                    
            # Parse type
            type_sugg = CategoryType.EXPENSE
            if data.get("type_suggestion") == "income":
                type_sugg = CategoryType.INCOME
                
            # Parse payment method
            method_sugg = PaymentMethod.CASH
            if data.get("payment_method_suggestion"):
                try:
                    method_sugg = PaymentMethod(data["payment_method_suggestion"])
                except Exception:
                    pass
            
            category_id = None
            if data.get("category_id"):
                try:
                    category_id = int(data["category_id"])
                except Exception:
                    pass
                    
            return ExtractedTransaction(
                amount=amount,
                transaction_date=data.get("transaction_date"),
                description=data.get("description"),
                type_suggestion=type_sugg,
                payment_method_suggestion=method_sugg,
                category_id=category_id,
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {text}")
            raise RuntimeError("Lỗi giải mã kết quả từ AI (không phải JSON hợp lệ).")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise RuntimeError(f"Lỗi khi xử lý ảnh bằng AI: {e}")
