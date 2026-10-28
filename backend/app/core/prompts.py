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
        "system_instruction": (
            "Bạn là trợ lý tài chính cá nhân FinAI dành cho người trẻ và người lao động tại Việt Nam.\n"
            "QUY TẮC BẮT BUỘC KHI ĐỊNH MỨC NGÂN SÁCH:\n"
            "1. Với các danh mục CHƯA CÓ lịch sử chi tiêu (avg_spent = 0 và last_spent = 0): BẮT BUỘC đề xuất mức tiết kiệm, hợp lý cho người trẻ/người lao động với mức thu nhập vừa phải. Tổng ngân sách toàn bộ các danh mục phải nằm trong khoảng 5,000,000 - 6,500,000 VNĐ.\n"
            "   - Ăn uống: 2,000,000 - 2,500,000 VNĐ.\n"
            "   - Nhà ở / Tiền phòng: 1,500,000 - 2,000,000 VNĐ.\n"
            "   - Đi lại / Xăng xe: 300,000 - 500,000 VNĐ.\n"
            "   - Mua sắm: 300,000 - 500,000 VNĐ.\n"
            "   - Giải trí / Cà phê: 200,000 - 300,000 VNĐ.\n"
            "   - Giáo dục / Sách vở: 200,000 - 300,000 VNĐ.\n"
            "   - Sức khỏe / Y tế: 200,000 - 300,000 VNĐ.\n"
            "   - Khác / Dự phòng: 200,000 VNĐ.\n"
            "2. Với danh mục ĐÃ CÓ dữ liệu lịch sử (avg_spent > 0 hoặc last_spent > 0): Đề xuất bám sát thực tế của người dùng kèm biên độ dự phòng an toàn 5-10%."
        ),
        "user_prompt_template": (
            "Dưới đây là danh sách các danh mục chi tiêu của người dùng cho tháng {target_month:02d}/{target_year} kèm mức chi trung bình (avg_spent) và tháng trước (last_spent):\n"
            "{items_json}\n\n"
            "Hãy phân tích và đưa ra recommended_amount (làm tròn đến 50,000 VNĐ) và reason (1 câu tiếng Việt ngắn gọn, khích lệ, thực tế).\n"
            "Trả về kết quả dưới dạng JSON array: [{{ 'id': <category_id>, 'recommended_amount': <number>, 'reason': '<lý do ngắn gọn>' }}]"
        ),
    },
    "receipt_ocr": {
        "prompt_template": (
            "Bạn là chuyên gia phân tích và trích xuất thông tin giao dịch tài chính từ hóa đơn, biên lai và phiếu chuyển tiền.\n"
            "Hãy trích xuất các thông tin sau từ hình ảnh được cung cấp và CHỈ trả về một đối tượng JSON hợp lệ duy nhất.\n\n"
            "Cấu trúc JSON Schema:\n"
            "{{\n"
            '    "amount": "Tổng số tiền thanh toán thực tế (dạng số, không kèm ký hiệu tiền tệ, ví dụ: 150000.50). BẮT BUỘC lấy số tiền tổng cộng cuối cùng (Total/Tổng tiền/Thành tiền). Trả về null nếu không tìm thấy.",\n'
            '    "transaction_date": "Ngày giao dịch theo định dạng YYYY-MM-DD (ví dụ: 2026-10-27), hoặc null nếu không tìm thấy.",\n'
            '    "description": "Tên cửa hàng hoặc mô tả ngắn gọn về giao dịch (tối đa 100 ký tự), ví dụ: \'Highlands Coffee\', \'Ăn trưa tại nhà hàng X\', \'Siêu thị VinMart\', hoặc null.",\n'
            '    "type_suggestion": "Bắt buộc là \'expense\' (chi tiêu) hoặc \'income\' (thu nhập). Hóa đơn mua sắm, ăn uống, dịch vụ thông thường là \'expense\'. Biên lai nhận tiền, lương, chuyển khoản đến là \'income\'.",\n'
            '    "payment_method_suggestion": "Bắt buộc là \'cash\' (tiền mặt) hoặc \'bank_transfer\' (chuyển khoản, thẻ, ví điện tử), hoặc null nếu không rõ.",\n'
            '    "category_id": "Số nguyên ID của danh mục phù hợp nhất từ danh sách được cung cấp, hoặc null nếu không xác định được."\n'
            "}}\n"
            "{categories_context}\n"
            "CHỈ trả về chuỗi JSON thuần túy, tuyệt đối KHÔNG định dạng markdown hay bọc trong khối code (```json). Không thêm bất kỳ văn bản nào trước hoặc sau."
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
    if isinstance(_PROMPT_CACHE, dict):
        return _PROMPT_CACHE

    config_path = _find_config_file()
    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                prompts = data.get("prompts")
                if isinstance(prompts, dict):
                    _PROMPT_CACHE = prompts
                    logger.info("Loaded prompts successfully from %s", config_path)
                    return prompts
        except Exception as e:
            logger.warning("Failed to parse %s: %s. Using fallback prompts.", config_path, e)

    _PROMPT_CACHE = dict(_FALLBACK_PROMPTS)
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
