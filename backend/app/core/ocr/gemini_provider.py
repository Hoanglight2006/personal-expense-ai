import json
import logging
from decimal import Decimal

import google.generativeai as genai
from pydantic import ValidationError

from app.config import settings
from app.core.ocr.base import ExtractedTransaction, OcrProvider
from app.models.enums import CategoryType, PaymentMethod

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
            categories_list = "\n".join([f"- ID: {c.id}, Tên: {c.name}, Loại: {c.type}" for c in categories])
            categories_context = f"""
        Here is the list of available categories for this user:
        {categories_list}
        
        Based on the items/products in the receipt and the store name, choose the MOST LOGICAL category_id from the list above. If you cannot determine it confidently, return null.
        """
        
        prompt = f"""
        You are an expert at extracting financial transaction details from receipts and invoices.
        Extract the following information from the provided image and return ONLY a valid JSON object.
        JSON Schema:
        {{
            "amount": "The total amount of the transaction as a number without currency symbols (e.g. 150000.50). Ensure you extract the FINAL Total amount. Return null if not found.",
            "transaction_date": "The date of the transaction in YYYY-MM-DD format, or null if not found",
            "description": "A short, concise description of the transaction (max 100 characters), e.g., 'Ăn trưa tại nhà hàng X', or null",
            "type_suggestion": "Must be either 'expense' or 'income'. For typical receipts (supermarkets, dining), it's 'expense'. For salary/transfer in, it's 'income'.",
            "payment_method_suggestion": "Must be one of 'cash', 'bank_transfer', 'credit_card', 'e_wallet', or null",
            "category_id": "The integer ID of the best matching category from the provided list, or null"
        }}
        {categories_context}
        Return ONLY the raw JSON without any markdown formatting or code blocks. Do not add any text before or after.
        """
        
        image_parts = [
            {
                "mime_type": "image/jpeg",
                "data": image_bytes
            }
        ]
        
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
