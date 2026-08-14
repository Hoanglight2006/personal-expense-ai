"""Gemini-powered AI chat service for financial assistant.

Provides the GeminiChatService class that builds financial context
from user transaction data and generates AI-powered responses.
"""

from datetime import date, timedelta
from decimal import Decimal

import google.generativeai as genai
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.models.user import User

SYSTEM_PROMPT = """Bạn là FinAI, trợ lý chi tiêu cá nhân thông minh và thân thiện.

QUY TẮC PHẠM VI & PHẢN HỒI (BẮT BUỘC):
1. VỀ TÀI CHÍNH & CHI TIÊU: Trả lời chính xác dựa trên dữ liệu thu/chi/số dư được cung cấp bên dưới. Chỉ đưa gợi ý tham khảo, không tư vấn tài chính chuyên nghiệp.
2. VỀ NHU CẦU TIÊU DÙNG / ĂN UỐNG / MUA SẮM (Ví dụ: "thèm ăn...", "muốn mua...", "đi chơi..."): Phản hồi ngắn gọn, vui vẻ 1 câu rồi NGAY LẬP TỨC bẻ lái về liên hệ với số dư/tổng chi tiêu thực tế của người dùng để nhắc nhở chi tiêu hợp lý.
3. VỀ CHỦ ĐỀ HOÀN TOÀN NGOÀI LỀ (Ví dụ: thời tiết, toán học, lịch sử, code, tin tức...): Lịch sự từ chối và nhắc người dùng quay lại chủ đề quản lý chi tiêu.

QUY TẮC ĐỘ DÀI & VĂN PHONG:
- Trả lời bằng tiếng Việt, ngắn gọn trong 2 - 4 câu (tối đa 100 từ).
- Không dùng markdown phức tạp, có thể dùng emoji sinh động.
- BẮT BUỘC phải viết trọn vẹn câu và kết thúc bằng dấu câu hợp lý (., !, ?). Tuyệt đối không dừng lửng lơ giữa chừng."""


def build_financial_context(db: Session, user_id: int) -> str:
    """Build a text summary of the user's financial data for AI context.

    Only sends aggregated/summarized data to protect user privacy.
    """
    today = date.today()
    first_of_month = today.replace(day=1)

    # --- Monthly totals by category ---
    monthly_stats = (
        db.query(
            Category.name,
            Transaction.type,
            sa_func.sum(Transaction.amount).label("total"),
            sa_func.count(Transaction.id).label("count"),
        )
        .join(
            Transaction,
            (Transaction.category_id == Category.id)
            & (Transaction.user_id == Category.user_id),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= first_of_month,
            Transaction.transaction_date <= today,
        )
        .group_by(Category.name, Transaction.type)
        .all()
    )

    total_income = Decimal("0")
    total_expense = Decimal("0")
    income_lines = []
    expense_lines = []

    for name, txn_type, total, count in monthly_stats:
        amount = total or Decimal("0")
        if txn_type == CategoryType.INCOME:
            total_income += amount
            income_lines.append(f"  - {name}: {amount:,.0f} VNĐ ({count} giao dịch)")
        else:
            total_expense += amount
            expense_lines.append(f"  - {name}: {amount:,.0f} VNĐ ({count} giao dịch)")

    # --- Recent transactions (last 5) ---
    recent = (
        db.query(Transaction, Category.name)
        .join(
            Category,
            (Transaction.category_id == Category.id)
            & (Transaction.user_id == Category.user_id),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
        )
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(5)
        .all()
    )

    recent_lines = []
    for txn, cat_name in recent:
        prefix = "Thu" if txn.type == CategoryType.INCOME else "Chi"
        recent_lines.append(
            f"  - [{txn.transaction_date}] {prefix}: {txn.amount:,.0f} VNĐ"
            f" — {cat_name}"
            + (f" ({txn.description})" if txn.description else "")
        )

    # --- Fetch user initial balance ---
    user = db.query(User).filter(User.id == user_id).first()
    initial_balance = getattr(user, "initial_balance", Decimal("0")) or Decimal("0")
    available_balance = initial_balance + total_income - total_expense

    # --- Build context text ---
    context_parts = [
        f"=== DỮ LIỆU TÀI CHÍNH THÁNG {today.month}/{today.year} ===",
        f"Ngày hôm nay: {today.strftime('%d/%m/%Y')}",
        f"SỐ DƯ BAN ĐẦU (TIỀN CÓ SẴN): {initial_balance:,.0f} VNĐ",
        "",
        f"TỔNG THU NHẬP THÁNG NÀY: {total_income:,.0f} VNĐ",
    ]
    if income_lines:
        context_parts.append("Chi tiết thu nhập theo danh mục:")
        context_parts.extend(income_lines)

    context_parts.append("")
    context_parts.append(f"TỔNG CHI TIÊU THÁNG NÀY: {total_expense:,.0f} VNĐ")
    if expense_lines:
        context_parts.append("Chi tiết chi tiêu theo danh mục:")
        context_parts.extend(expense_lines)

    context_parts.append("")
    context_parts.append(f"CHÊNH LỆCH THU - CHI THÁNG NÀY: {(total_income - total_expense):,.0f} VNĐ")
    context_parts.append(f"SỐ DƯ KHẢ DỤNG HIỆN TẠI (Số dư ban đầu + Thu - Chi): {available_balance:,.0f} VNĐ")

    if recent_lines:
        context_parts.append("")
        context_parts.append("5 GIAO DỊCH GẦN NHẤT:")
        context_parts.extend(recent_lines)

    return "\n".join(context_parts)


class GeminiChatService:
    """Handles AI chat interactions via the Gemini API."""

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model_name = settings.GEMINI_MODEL

    async def generate_reply(
        self,
        user_message: str,
        financial_context: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Generate an AI reply given the user message and financial context."""

        full_system = f"{SYSTEM_PROMPT}\n\n{financial_context}"
        contents = []

        if conversation_history:
            for msg in conversation_history[-10:]:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [msg["content"]]})

        contents.append({"role": "user", "parts": [user_message]})

        candidate_models = [
            self._model_name,
            "gemini-3.5-flash",
            "gemini-flash-latest",
        ]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        last_error = None
        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    system_instruction=full_system,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1000,
                        temperature=0.7,
                    ),
                )
                response = await model.generate_content_async(contents)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                last_error = e
                continue

        return f"Xin lỗi, mình đang gặp sự cố kết nối AI. Vui lòng thử lại sau! 🙏 ({type(last_error).__name__ if last_error else 'Unknown'})"


