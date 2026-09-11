"""Prompt Manager Service.

Loads, caches, and formats prompts stored externally in config/prompts.json
to ensure full decoupling of prompts from application code.
Includes a complete fallback registry to guarantee zero downtime.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default hardcoded fallbacks to guarantee resilience if config file is missing
_FALLBACK_PROMPTS: dict[str, dict[str, str]] = {
    "finai_chat": {
        "system_prompt": (
            "Bạn là FinAI, trợ lý chi tiêu cá nhân thông minh và thân thiện.\n\n"
            "QUY TẮC PHẠM VI & PHẢN HỒI (BẮT BUỘC):\n"
            "1. VỀ TÀI CHÍNH & CHI TIÊU: Trả lời chính xác dựa trên dữ liệu thu/chi/số dư được cung cấp bên dưới. Chỉ đưa gợi ý tham khảo, không tư vấn tài chính chuyên nghiệp.\n"
            "2. VỀ NHU CẦU TIÊU DÙNG / ĂN UỐNG / MUA SẮM (Ví dụ: \"thèm ăn...\", \"muốn mua...\", \"đi chơi...\"): Phản hồi ngắn gọn, vui vẻ 1 câu rồi NGAY LẬP TỨC bẻ lái về liên hệ với số dư/tổng chi tiêu thực tế của người dùng để nhắc nhở chi tiêu hợp lý.\n"
            "3. VỀ CHỦ ĐỀ HOÀN TOÀN NGOÀI LỀ (Ví dụ: thời tiết, toán học, lịch sử, code, tin tức...): Lịch sự từ chối và nhắc người dùng quay lại chủ đề quản lý chi tiêu.\n\n"
            "QUY TẮC ĐỘ DÀI & VĂN PHONG:\n"
            "- Trả lời bằng tiếng Việt, ngắn gọn trong 2 - 4 câu (tối đa 100 từ).\n"
            "- Không dùng markdown phức tạp, có thể dùng emoji sinh động.\n"
            "- BẮT BUỘC phải viết trọn vẹn câu và kết thúc bằng dấu câu hợp lý (., !, ?). Tuyệt đối không dừng lửng lơ giữa chừng."
        ),
    },
    "monthly_report": {
        "system_instruction": "Bạn là trợ lý chi tiêu cá nhân. Chỉ đưa gợi ý tham khảo, không tư vấn tài chính chuyên nghiệp.",
        "user_prompt_template": (
            "Dữ liệu chi tiêu tháng:\n{summary_text}\n\n"
            "Hãy tóm tắt xu hướng và gợi ý 3 điểm cần điều chỉnh.\n\n"
            "Trả lời dưới định dạng JSON với cấu trúc sau:\n"
            "{{\n"
            '  "overview": "Tóm tắt tổng quan tình hình tài chính tháng này trong 1-2 câu",\n'
            '  "trend_analysis": "Phân tích cụ thể xu hướng thu/chi, so sánh với tháng trước và danh mục chi tiêu lớn nhất",\n'
            '  "adjustments": [\n'
            '    "Gợi ý điều chỉnh hành động 1 (cụ thể, thiết thực)",\n'
            '    "Gợi ý điều chỉnh hành động 2 (cụ thể, thiết thực)",\n'
            '    "Gợi ý điều chỉnh hành động 3 (cụ thể, thiết thực)"\n'
            "  ],\n"
            '  "conclusion": "Lời khuyên đúc kết tài chính ngắn gọn và động lực tiết kiệm cho tháng tới"\n'
            "}}"
        ),
    },
    "budget_recommendations": {
        "system_instruction": "Bạn là trợ lý tài chính cá nhân thông minh. Đưa ra gợi ý hạn mức ngân sách hàng tháng hợp lý, thực tế và tiết kiệm.",
        "user_prompt_template": (
            "Dưới đây là danh sách các danh mục chi tiêu của người dùng cho tháng {target_month:02d}/{target_year} kèm mức chi trung bình (avg_spent) và tháng trước (last_spent):\n"
            "{items_json}\n\n"
            "Hãy đưa ra mức ngân sách đề xuất (recommended_amount dạng số làm tròn đến 10,000 hoặc 50,000 VNĐ) và lý do ngắn gọn (reason trong 1 câu tiếng Việt).\n"
            "Trả về kết quả dưới dạng JSON array: [{{ 'id': <category_id>, 'recommended_amount': <number>, 'reason': '<lý do ngắn gọn>' }}]"
        ),
    },
    "receipt_ocr": {
        "prompt_template": (
            "You are an expert at extracting financial transaction details from receipts and invoices.\n"
            "Extract the following information from the provided image and return ONLY a valid JSON object.\n"
            "JSON Schema:\n"
            "{{\n"
            '    "amount": "The total amount of the transaction as a number without currency symbols (e.g. 150000.50). Ensure you extract the FINAL Total amount. Return null if not found.",\n'
            '    "transaction_date": "The date of the transaction in YYYY-MM-DD format, or null if not found",\n'
            '    "description": "A short, concise description of the transaction (max 100 characters), e.g., \'Ăn trưa tại nhà hàng X\', or null",\n'
            '    "type_suggestion": "Must be either \'expense\' or \'income\'. For typical receipts (supermarkets, dining), it\'s \'expense\'. For salary/transfer in, it\'s \'income\'.",\n'
            '    "payment_method_suggestion": "Must be one of \'cash\', \'bank_transfer\', \'credit_card\', \'e_wallet\', or null",\n'
            '    "category_id": "The integer ID of the best matching category from the provided list, or null"\n'
            "}}\n"
            "{categories_context}\n"
            "Return ONLY the raw JSON without any markdown formatting or code blocks. Do not add any text before or after."
        )
    },
}

_PROMPT_CACHE: dict[str, Any] | None = None


def _find_config_file() -> Path | None:
    """Locate config/prompts.json relative to current file or workspace."""
    base_dir = Path(__file__).resolve()
    # Check parent hierarchy (backend/app/core -> backend/app -> backend -> project_root)
    candidates = [
        base_dir.parents[3] / "config" / "prompts.json",
        base_dir.parents[2] / "config" / "prompts.json",
        Path.cwd() / "config" / "prompts.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def get_all_prompts() -> dict[str, Any]:
    """Load and return all prompts from JSON configuration or fallback."""
    global _PROMPT_CACHE
    if _PROMPT_CACHE is not None:
        return _PROMPT_CACHE

    config_path = _find_config_file()
    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _PROMPT_CACHE = data.get("prompts", {})
                logger.info("Loaded prompts successfully from %s", config_path)
                return _PROMPT_CACHE
        except Exception as e:
            logger.warning("Failed to parse %s: %s. Using fallback prompts.", config_path, e)

    _PROMPT_CACHE = _FALLBACK_PROMPTS
    return _PROMPT_CACHE


def get_prompt(group: str, key: str, default: str = "") -> str:
    """Get a prompt string by group and key."""
    prompts = get_all_prompts()
    group_data = prompts.get(group, {})
    if isinstance(group_data, dict):
        val = group_data.get(key)
        if val is not None:
            return str(val)

    # Check fallback if missing
    fallback_group = _FALLBACK_PROMPTS.get(group, {})
    return fallback_group.get(key, default)


def format_prompt(group: str, key: str, **kwargs) -> str:
    """Get a prompt template and format it with kwargs."""
    template = get_prompt(group, key)
    if not template:
        return ""
    try:
        return template.format(**kwargs)
    except Exception as e:
        logger.error("Error formatting prompt %s.%s: %s", group, key, e)
        return template
