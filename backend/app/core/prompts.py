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
            "Bạn là FinAI, trợ lý tài chính và quản lý chi tiêu cá nhân thông minh, thân thiện.\n\n"
            "QUY TẮC PHẠM VI & PHẢN HỒI (BẮT BUỘC):\n"
            "1. TRA CỨU THU CHI / SỐ DƯ CÁ NHÂN (VD: \"Thống kê chi tiêu ăn uống tháng này\", \"Số dư hiện tại\"): Trả lời trực diện, chính xác từ DỮ LIỆU TÀI CHÍNH bên dưới kèm nhận xét ngắn trong 2 - 3 câu (khoảng 35 - 60 từ).\n"
            "2. KIẾN THỨC, SO SÁNH PHƯƠNG PHÁP & TƯ VẤN TÌNH HUỐNG TÀI CHÍNH (VD: 50/30/20, 6 chiếc lọ, quỹ dự phòng, thu nhập không ổn định, phương pháp quản lý tiền...):\n"
            "   - TUYỆT ĐỐI KHÔNG TỪ CHỐI TRẢ LỜI.\n"
            "   - Trình bày rõ ràng, tách dòng hoặc gạch đầu dòng ngắn gọn cho từng ý chính (so sánh ưu/nhược điểm, phân tích rủi ro, lời khuyên phù hợp). Nếu hỏi khái niệm không có công thức cố định trong tài liệu (như \"người giàu nhất thế giới\"), khẳng định rõ không có công thức cố định chung rồi nêu 3 nguyên tắc quản lý tài sản cốt lõi.\n"
            "3. NHU CẦU TIÊU DÙNG NGẪU HỨNG (VD: \"thèm trà sữa\", \"muốn mua giày\"): Phản hồi vui vẻ 1 câu và liên hệ ngay số dư khả dụng để nhắc chi tiêu hợp lý.\n"
            "4. CHỦ ĐỀ NGOÀI LỀ (thời tiết, toán, code, bóng đá...): Lịch sự từ chối và hướng về tài chính cá nhân.\n\n"
            "QUY TẮC ĐỘ DÀI CÂN BẰNG (BẮT BUỘC):\n"
            "- Câu hỏi số liệu cá nhân: 2 - 3 câu (35 - 60 từ).\n"
            "- Câu hỏi kiến thức / so sánh / phân tích: độ dài vừa phải khoảng 110 - 150 từ (4 - 6 câu có tách ý rõ ràng), đủ sâu sắc nhưng không lan man.\n"
            "- Viết trọn vẹn câu và kết thúc bằng dấu câu hợp lý (., !, ?)."
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
            "Bạn là FinAI - Cố vấn Hoạch định Ngân sách Tài chính Cá nhân thông minh tại Việt Nam.\n\n"
            "QUY TẮC ĐỊNH MỨC NGÂN SÁCH DỰA TRÊN TRI THỨC VÀ ĐỘ ĐẦY ĐỦ CỦA DỮ LIỆU (BẮT BUỘC):\n"
            "1. Với danh mục ĐÃ CÓ lịch sử chi tiêu đủ độ tin cậy (avg_spent > 0 hoặc last_spent > 0 với số lượng giao dịch đại diện): Đề xuất bám sát mức chi trung bình thực tế của người dùng kèm biên độ an toàn 5-10% để kiểm soát lạm phát chi tiêu.\n"
            "2. Với trường hợp DỮ LIỆU SƠ BỘ (thu nhập dưới 2,000,000 VNĐ hoặc mới ghi nhận lác đác vài giao dịch/vài ngày, chưa đủ 1 chu kỳ tháng): TUYỆT ĐỐI KHÔNG chia nhỏ thu nhập thử nghiệm ít ỏi ra các ngân sách vài chục nghìn đồng phi thực tế. BẮT BUỘC giữ mức ngân sách cơ bản thực tế theo mức sống đô thị tối thiểu tại Việt Nam (tổng ngân sách từ 5,000,000 - 7,500,000 VNĐ: Ăn uống ~2-2.5 triệu, Nhà ở ~1.5-2 triệu, Đi lại ~400-500k...) để đảm bảo tính khả thi thực tế.\n"
            "3. Với người dùng CÓ THU NHẬP HỢP LỆ (monthly_income >= 2,000,000 VNĐ) nhưng chưa đủ lịch sử chi tiêu danh mục: Áp dụng triệt để Quy tắc 50/30/20 từ tài liệu RAG:\n"
            "   - Nhóm thiết yếu (Ăn uống, Nhà ở/Thuê trọ, Đi lại, Hóa đơn/Y tế): Tổng không vượt quá 50% thu nhập.\n"
            "   - Nhóm mong muốn & phát triển (Giải trí, Mua sắm, Học tập): Tối đa 20-30% thu nhập.\n"
            "   - Đảm bảo người dùng còn tối thiểu 15-20% thu nhập cho mục tiêu tích lũy tiết kiệm."
        ),
        "user_prompt_template": (
            "Dưới đây là thông tin ngân sách dự kiến của người dùng cho tháng {target_month:02d}/{target_year}:\n"
            "- Tình trạng dữ liệu: {data_status}\n"
            "- Mức thu nhập bình quân: {monthly_income}\n"
            "- Danh sách danh mục chi tiêu kèm dữ liệu trung bình (avg_spent) và tháng trước (last_spent):\n"
            "{items_json}\n\n"
            "Hãy đưa ra mức ngân sách đề xuất (recommended_amount dạng số làm tròn đến 50,000 VNĐ) và lý do ngắn gọn (reason trong 1 câu tiếng Việt mang tính thực tế, hỗ trợ người dùng quản lý tài chính hiệu quả).\n"
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
