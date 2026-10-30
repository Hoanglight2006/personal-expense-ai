"""Monthly financial report generator with Gemini AI insights and health score scoring.
"""

from __future__ import annotations

import asyncio
import calendar
import json
import re
from datetime import date
from app.core.timezone import local_today, datetime, timezone
from decimal import Decimal
from typing import Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.ai_chat import mask_sensitive_data
from app.core.prompts import format_prompt, get_prompt
from app.core.rag import retrieve_contextual_report_knowledge
from app.models.ai_report import AIReport
from app.models.budget import Budget
from app.models.saving_contribution import SavingContribution
from app.models.saving_goal import SavingGoal
from app.models.saving_withdrawal import SavingWithdrawal
from app.models.category import Category
from app.models.enums import CategoryType, GoalStatus, ReportType
from app.models.transaction import Transaction
from app.schemas.ai import MonthlyReportResponse

SYSTEM_REPORT_PROMPT = get_prompt("monthly_report", "system_instruction")

FOCUS_SYSTEM_INSTRUCTIONS = {
    "comprehensive": (
        "Bạn là FinAI - Cố vấn Hoạch định Tài chính Toàn diện.\n"
        "Đánh giá tổng thể bức tranh tài chính 360 độ: cân đối thu nhập, tỷ trọng các nhóm chi tiêu, tỷ lệ tiết kiệm và sự lành mạnh của dòng tiền.\n"
        "Văn phong khách quan, trung lập, khoa học và giàu tính xây dựng.\n"
        "Chỉ đưa ra phân tích tham khảo, không tư vấn tài chính chuyên nghiệp."
    ),
    "saving": (
        "Bạn là FinAI - Chuyên gia Tối Ưu Cắt Giảm Chi Phí & Thợ Săn Tiết Kiệm (Frugality Specialist).\n"
        "Mục tiêu tối thượng: Tìm kiếm các khoản chi tiêu hao phí, các thói quen tiêu dùng ngẫu hứng và thúc đẩy thắt chặt chi tiêu tối đa để tích lũy thặng dư.\n"
        "Văn phong sắc sảo, kiên quyết, thực tế, tập trung 100% vào việc cắt giảm chi phí và tối đa hóa số tiền tiết kiệm.\n"
        "Chỉ đưa ra phân tích tham khảo, không tư vấn tài chính chuyên nghiệp."
    ),
    "risk": (
        "Bạn là FinAI - Chuyên gia Kiểm Soát Rủi Ro & An Toàn Dòng Tiền (Financial Risk Officer).\n"
        "Mục tiêu tối thượng: Phát hiện các lỗ hổng tài chính, cảnh báo bội chi ngân sách, nguy cơ cạn kiệt thanh khoản và thúc đẩy xây dựng quỹ dự phòng khẩn cấp.\n"
        "Văn phong thận trọng, cảnh báo nghiêm túc, đặt an toàn tài chính, phòng thủ và quản lý thanh khoản lên hàng đầu.\n"
        "Chỉ đưa ra phân tích tham khảo, không tư vấn tài chính chuyên nghiệp."
    ),
}



def calculate_monthly_financial_summary(
    db: Session, user_id: int, year: int, month: int
) -> dict[str, Any]:
    """Calculate deterministic financial stats for a given month."""
    first_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last_date = date(year, month, last_day)

    # 1. Total income & expense
    totals = (
        db.query(
            Transaction.type,
            sa_func.coalesce(sa_func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= first_date,
            Transaction.transaction_date <= last_date,
        )
        .group_by(Transaction.type)
        .all()
    )

    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")
    for txn_type, total in totals:
        amt = Decimal(str(total or 0)).quantize(Decimal("0.01"))
        if txn_type == CategoryType.INCOME or txn_type == CategoryType.INCOME.value:
            total_income = amt
        else:
            total_expense = amt

    net_savings = total_income - total_expense
    savings_rate = (
        round(float((net_savings / total_income) * 100), 1)
        if total_income > Decimal("0.00")
        else 0.0
    )

    # 2. Category Breakdown
    cat_breakdown = (
        db.query(
            Category.name,
            Category.icon,
            Category.color,
            Transaction.type,
            sa_func.sum(Transaction.amount).label("cat_total"),
            sa_func.count(Transaction.id).label("cat_count"),
        )
        .join(
            Category,
            (Transaction.category_id == Category.id)
            & (Transaction.user_id == Category.user_id),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= first_date,
            Transaction.transaction_date <= last_date,
        )
        .group_by(Category.name, Category.icon, Category.color, Transaction.type)
        .order_by(sa_func.sum(Transaction.amount).desc())
        .all()
    )

    top_expenses: list[dict[str, Any]] = []
    top_incomes: list[dict[str, Any]] = []
    for name, icon, color, txn_type, cat_total, cat_count in cat_breakdown:
        amt = Decimal(str(cat_total or 0)).quantize(Decimal("0.01"))
        pct = (
            round(float((amt / total_expense) * 100), 1)
            if txn_type == CategoryType.EXPENSE and total_expense > 0
            else 0.0
        )
        item = {
            "name": name,
            "icon": icon,
            "color": color,
            "amount": amt,
            "count": cat_count,
            "percentage": pct,
        }
        if txn_type == CategoryType.EXPENSE or txn_type == CategoryType.EXPENSE.value:
            top_expenses.append(item)
        else:
            top_incomes.append(item)

    # 3. Budgets status for this month
    budgets = (
        db.query(Budget, Category.name)
        .join(Category, Budget.category_id == Category.id)
        .filter(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year,
        )
        .all()
    )
    exceeded_budgets_count = 0
    budget_details = []
    for b, cat_name in budgets:
        spent = next((e["amount"] for e in top_expenses if e["name"] == cat_name), Decimal("0.00"))
        if spent > b.amount:
            exceeded_budgets_count += 1
        budget_details.append({
            "category": cat_name,
            "budget": b.amount,
            "spent": spent,
            "is_exceeded": spent > b.amount,
        })

    # 4. Compare with previous month
    prev_m = month - 1
    prev_y = year
    if prev_m == 0:
        prev_m = 12
        prev_y -= 1
    prev_first = date(prev_y, prev_m, 1)
    prev_last_day = calendar.monthrange(prev_y, prev_m)[1]
    prev_last = date(prev_y, prev_m, prev_last_day)

    prev_totals = (
        db.query(
            Transaction.type,
            sa_func.coalesce(sa_func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= prev_first,
            Transaction.transaction_date <= prev_last,
        )
        .group_by(Transaction.type)
        .all()
    )
    prev_expense = Decimal("0.00")
    for txn_type, total in prev_totals:
        if txn_type == CategoryType.EXPENSE or txn_type == CategoryType.EXPENSE.value:
            prev_expense = Decimal(str(total or 0)).quantize(Decimal("0.01"))

    expense_growth_pct = (
        round(float(((total_expense - prev_expense) / prev_expense) * 100), 1)
        if prev_expense > 0
        else 0.0
    )

    # 5. Saving Goals contributions and active count
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59)
    saving_deposit_total = (
        db.query(sa_func.coalesce(sa_func.sum(SavingContribution.amount), 0))
        .join(SavingGoal, SavingContribution.saving_goal_id == SavingGoal.id)
        .filter(
            SavingGoal.user_id == user_id,
            SavingContribution.created_at >= start_dt,
            SavingContribution.created_at <= end_dt,
        )
        .scalar()
    )
    saving_withdraw_total = (
        db.query(sa_func.coalesce(sa_func.sum(SavingWithdrawal.amount), 0))
        .join(SavingGoal, SavingWithdrawal.saving_goal_id == SavingGoal.id)
        .filter(
            SavingGoal.user_id == user_id,
            SavingWithdrawal.created_at >= start_dt,
            SavingWithdrawal.created_at <= end_dt,
        )
        .scalar()
    )
    gross_deposited = Decimal(str(saving_deposit_total or 0)).quantize(Decimal("0.01"))
    gross_withdrawn = Decimal(str(saving_withdraw_total or 0)).quantize(Decimal("0.01"))
    net_saving_deposited = max(Decimal("0.00"), gross_deposited - gross_withdrawn).quantize(Decimal("0.01"))
    total_saving_deposited = net_saving_deposited

    active_goals_count = (
        db.query(sa_func.count(SavingGoal.id))
        .filter(
            SavingGoal.user_id == user_id,
            SavingGoal.status == GoalStatus.ACTIVE,
        )
        .scalar()
        or 0
    )

    # 6. Sample size & preliminary evaluation check
    expense_txn_count = sum(item["count"] for item in top_expenses)
    is_preliminary = (
        total_expense < Decimal("500000.00")
        or expense_txn_count < 5
        or (total_income == Decimal("0.00") and total_expense == Decimal("0.00"))
    )

    # 6. Financial Health Score calculation (0 - 100)
    if total_income == Decimal("0.00") and total_expense == Decimal("0.00"):
        score = 50
        health_status = "Chưa có dữ liệu"
    elif is_preliminary:
        score = 70
        health_status = "Đang theo dõi"
    else:
        score = 70
        if savings_rate >= 30:
            score += 20
        elif savings_rate >= 20:
            score += 15
        elif savings_rate >= 10:
            score += 10
        elif savings_rate > 0:
            score += 5
        elif savings_rate < 0:
            score -= 25

        if exceeded_budgets_count == 0 and len(budgets) > 0:
            score += 10
        elif exceeded_budgets_count > 0:
            score -= (exceeded_budgets_count * 10)

        score = max(10, min(98, score))

        if score >= 80:
            health_status = "Xuất sắc"
        elif score >= 65:
            health_status = "Tốt"
        elif score >= 45:
            health_status = "Cần chú ý"
        else:
            health_status = "Báo động"

    return {
        "year": year,
        "month": month,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": net_savings,
        "savings_rate": savings_rate,
        "top_expenses": top_expenses,
        "top_incomes": top_incomes,
        "budgets": budget_details,
        "exceeded_budgets_count": exceeded_budgets_count,
        "prev_expense": prev_expense,
        "expense_growth_pct": expense_growth_pct,
        "expense_txn_count": expense_txn_count,
        "is_preliminary": is_preliminary,
        "health_score": score,
        "health_status": health_status,
        "total_saving_deposited": total_saving_deposited,
        "saving_gross_deposited": gross_deposited,
        "saving_gross_withdrawn": gross_withdrawn,
        "active_goals_count": active_goals_count,
    }


async def generate_monthly_ai_report(
    db: Session,
    user_id: int,
    month_str: str,
    focus: str = "comprehensive",
    get_model_fn=None,
) -> MonthlyReportResponse:
    """Generate an AI monthly spending report adhering to REQUIREMENTS.md with focus differentiation."""
    try:
        parts = month_str.split("-")
        year = int(parts[0])
        month = int(parts[1])
    except (ValueError, IndexError):
        year, month = local_today().year, local_today().month

    summary = calculate_monthly_financial_summary(db, user_id, year, month)

    top_exp_lines = [
        f"- {e['name']}: {e['amount']:,.0f} đ ({e['percentage']}%)"
        for e in summary["top_expenses"][:5]
    ]

    # Format Budget details & identify overages / warnings
    budget_lines = []
    exceeded_lines = []
    warning_lines = []
    for b in summary.get("budgets", []):
        cat = b["category"]
        spent_val = b["spent"]
        limit_val = b["budget"]
        pct = round(float((spent_val / limit_val) * 100), 1) if limit_val > 0 else 0.0
        if b["is_exceeded"]:
            over_val = spent_val - limit_val
            line = f"- {cat}: ĐÃ VƯỢT HẠN MỨC! Đã chi {spent_val:,.0f} đ / Ngân sách {limit_val:,.0f} đ ({pct}%, vượt {over_val:,.0f} đ)"
            budget_lines.append(line)
            exceeded_lines.append(f"'{cat}' (chi {spent_val:,.0f} đ / hạn mức {limit_val:,.0f} đ, vượt {over_val:,.0f} đ - {pct}%)")
        elif limit_val > 0 and spent_val >= limit_val * Decimal("0.8"):
            line = f"- {cat}: CẢNH BÁO SẮP CHẠM TRẦN (>= 80%)! Đã chi {spent_val:,.0f} đ / Ngân sách {limit_val:,.0f} đ ({pct}%)"
            budget_lines.append(line)
            warning_lines.append(f"'{cat}' (đã tiêu {pct}% hạn mức)")
        else:
            line = f"- {cat}: Trong hạn mức an toàn (Đã chi {spent_val:,.0f} đ / Ngân sách {limit_val:,.0f} đ - {pct}%)"
            budget_lines.append(line)

    budgets_text = (
        "Tình hình thực hiện hạn mức ngân sách:\n" + ("\n".join(budget_lines) if budget_lines else "Người dùng chưa thiết lập hạn mức ngân sách cho tháng này.")
    )

    summary_text = (
        f"Tháng: {month:02d}/{year}\n"
        f"Tổng thu nhập: {summary['total_income']:,.0f} VNĐ\n"
        f"Tổng chi tiêu: {summary['total_expense']:,.0f} VNĐ\n"
        f"Tiết kiệm thặng dư: {summary['net_savings']:,.0f} VNĐ (Tỷ lệ: {summary['savings_rate']}%)\n"
        f"Tích lũy vào mục tiêu tiết kiệm (Nạp - Rút): {summary['total_saving_deposited']:,.0f} VNĐ ({summary['active_goals_count']} mục tiêu đang chạy"
        + (f" | Đã nạp {summary['saving_gross_deposited']:,.0f} đ, đã rút {summary['saving_gross_withdrawn']:,.0f} đ" if summary.get('saving_gross_withdrawn', 0) > 0 else "")
        + ")\n"
        f"So với tháng trước ({summary['prev_expense']:,.0f} VNĐ): Biến động {summary['expense_growth_pct']:+.1f}%\n"
        f"Top danh mục chi tiêu:\n" + ("\n".join(top_exp_lines) if top_exp_lines else "Chưa có giao dịch chi tiêu.") + "\n\n"
        + budgets_text
    )

    focus_directives = {
        "comprehensive": (
            "TRỌNG TÂM PHÂN TÍCH: [TOÀN DIỆN 360 ĐỘ].\n"
            "- Đánh giá cân đối đa chiều giữa cơ cấu thu nhập, chi tiêu, tỷ lệ tiết kiệm và phân bổ các danh mục chính.\n"
            "- 3 khuyến nghị (adjustments) phải chia đều: 1 điểm cho danh mục chi tiêu lớn nhất, 1 điểm cho phân bổ ngân sách các nhu cầu, 1 điểm cho kế hoạch tích lũy."
        ),
        "saving": (
            "TRỌNG TÂM PHÂN TÍCH: [TỐI ƯU TIẾT KIỆM & CẮT GIẢM CHI PHÍ].\n"
            "- Tập trung soi xét các khoản chi tiêu chiếm tỷ trọng lớn hoặc các danh mục ngốn tiền nhất.\n"
            "- 3 khuyến nghị (adjustments) PHẢI LÀ 3 BIỆN PHÁP CẮT GIẢM CHI PHÍ CỤ THỂ, THỰC CHIẾN (ví dụ: tự nấu ăn, trì hoãn mua sắm 48h, cắt giảm dịch vụ thừa, săn deal/giảm giá, đặt hạn mức thắt lưng buộc bụng)."
        ),
        "risk": (
            "TRỌNG TÂM PHÂN TÍCH: [CẢNH BÁO RỦI RO & AN TOÀN TÀI CHÍNH].\n"
            "- Tập trung đánh giá nguy cơ bội chi ngân sách, rủi ro thâm hụt số dư nếu thu nhập biến động hoặc có biến cố khẩn cấp.\n"
            "- 3 khuyến nghị (adjustments) PHẢI LÀ 3 BIỆN PHÁP PHÒNG THỦ & AN TOÀN TÀI CHÍNH (ví dụ: cấp thiết lập quỹ dự phòng khẩn cấp 3-6 tháng, cài đặt trần cảnh báo khi chi tiêu chạm 75-80%, tuyệt đối tránh nợ tiêu dùng tín dụng)."
        ),
    }
    selected_directive = focus_directives.get(focus, focus_directives["comprehensive"])

    # Real-time awareness based on local date
    today = local_today()
    is_current_month = (year == today.year and month == today.month)
    is_past_month = (year < today.year) or (year == today.year and month < today.month)

    # Budget overage & warning directive
    budget_directive = ""
    if exceeded_lines:
        budget_directive = (
            f"\n\n[CẢNH BÁO BẮT BUỘC - VƯỢT HẠN MỨC NGÂN SÁCH]:\n"
            f"Người dùng ĐÃ VƯỢT HẠN MỨC NGÂN SÁCH ở các danh mục: {', '.join(exceeded_lines)}.\n"
            f"- BẮT BUỘC: Trong phần overview hoặc trend_analysis, BẠN PHẢI CHỈ ĐÍCH DANH danh mục bị vỡ kế hoạch ngân sách và số tiền vượt.\n"
            f"- BẮT BUỘC: Trong phần adjustments, PHẢI CÓ ÍT NHẤT 1 KHUYẾN NGHỊ TRỰC DIỆN nhắc nhở người dùng cắt giảm chi tiêu ngay lập tức ở danh mục {', '.join(exceeded_lines)} để đưa chi tiêu về tầm kiểm soát."
        )
    elif warning_lines:
        budget_directive = (
            f"\n\n[LƯU Ý NGÂN SÁCH SẮP CHẠM TRẦN]:\n"
            f"Các danh mục sắp chạm trần ngân sách: {', '.join(warning_lines)}.\n"
            f"- Hãy nhắc nhở người dùng chú ý hạn chế chi tiêu ở các danh mục này trước khi hết tháng."
        )

    preliminary_notice = ""
    if summary["is_preliminary"]:
        if is_current_month:
            if today.day <= 7:
                preliminary_notice = (
                    f"\n\n[LƯU Ý BỐI CẢNH THỜI GIAN - ĐẦU THÁNG]:\n"
                    f"Hôm nay là ngày {today.day}/{today.month}/{year} (những ngày đầu chu kỳ tháng mới). "
                    f"Người dùng mới ghi chép {summary['expense_txn_count']} giao dịch với tổng chi {summary['total_expense']:,.0f} đ.\n"
                    f"- Sức khỏe tài chính đang ở trạng thái 'Đang theo dõi' (70/100).\n"
                    f"- TUYỆT ĐỐI KHÔNG khen ngợi 'ấn tượng', 'xuất sắc' hay 'quản lý tốt' vì dữ liệu mới chỉ là vài ngày đầu tháng.\n"
                    f"- Phần overview: Khẳng định rõ tình trạng chi tiêu đang ở giai đoạn sơ bộ đầu tháng {month:02d}/{year}.\n"
                    f"- Phần adjustments: Khuyên người dùng tiếp tục ghi chép đầy đủ các khoản phát sinh hàng ngày trong suốt cả tháng."
                )
            else:
                preliminary_notice = (
                    f"\n\n[LƯU Ý BỐI CẢNH THỜI GIAN - GIỮA/CUỐI THÁNG NHƯNG DỮ LIỆU ÍT]:\n"
                    f"Hôm nay đã là ngày {today.day}/{today.month}/{year} (đã về giữa/cuối tháng), nhưng hệ thống mới ghi nhận {summary['expense_txn_count']} giao dịch chi tiêu với tổng số tiền {summary['total_expense']:,.0f} đ.\n"
                    f"- KHÔNG ĐƯỢC nói đây là 'vừa mới bắt đầu tháng' hay 'đầu kỳ', vì hôm nay đã là ngày {today.day}.\n"
                    f"- Nhận định rõ: Chi tiêu ghi nhận ở mức rất ít hoặc người dùng chưa cập nhật đầy đủ các khoản phát sinh hàng ngày.\n"
                    f"- Sức khỏe tài chính đang ở trạng thái 'Đang theo dõi' (70/100).\n"
                    f"- Phần adjustments: Khuyên người dùng kiểm tra và ghi chép bổ sung các chi phí thực tế đã chi trong tháng để bức tranh tài chính chính xác nhất."
                )
        elif is_past_month:
            preliminary_notice = (
                f"\n\n[LƯU Ý BỐI CẢNH THỜI GIAN - THÁNG ĐÃ KẾT THÚC]:\n"
                f"Tháng {month:02d}/{year} là tháng trong quá khứ đã kết thúc. Trong cả tháng này chỉ ghi nhận {summary['expense_txn_count']} giao dịch với tổng chi {summary['total_expense']:,.0f} đ.\n"
                f"- TUYỆT ĐỐI KHÔNG dùng từ 'đầu tháng', 'đầu kỳ' hay 'chu kỳ mới bắt đầu'.\n"
                f"- Đánh giá dựa trên tổng kết thực tế đã ghi nhận của tháng này."
            )

    rag_context, applied_benchmarks = retrieve_contextual_report_knowledge(summary, focus=focus)
    user_prompt = (
        (f"{rag_context}\n\n" if rag_context else "") +
        f"{selected_directive}{budget_directive}{preliminary_notice}\n\n"
        + format_prompt("monthly_report", "user_prompt_template", summary_text=summary_text)
    )

    # Differentiated Fallbacks based on focus, timing, and budget status
    if is_current_month and today.day <= 7:
        prelim_text = "Dữ liệu chi tiêu đang ở giai đoạn đầu tháng, cần tiếp tục ghi nhận để theo dõi bức tranh tài chính."
    elif is_current_month and today.day > 7:
        prelim_text = f"Đã qua ngày {today.day}/{month} nhưng hệ thống mới ghi nhận {summary['expense_txn_count']} giao dịch, cần kiểm tra và ghi chép bổ sung các chi phí thực tế."
    elif is_past_month:
        prelim_text = f"Dữ liệu tháng {month:02d}/{year} đã chốt sổ với số lượng ghi chép khá ít ({summary['expense_txn_count']} giao dịch)."
    else:
        prelim_text = "Dữ liệu chi tiêu đang ở giai đoạn sơ bộ."

    budget_warning_text = ""
    if summary["exceeded_budgets_count"] > 0:
        over_names = [b["category"] for b in summary["budgets"] if b["is_exceeded"]]
        budget_warning_text = f" Cảnh báo: Có {summary['exceeded_budgets_count']} danh mục đã vượt hạn mức ngân sách ({', '.join(over_names)})."

    if focus == "saving":
        overview = (
            f"Báo cáo tối ưu tiết kiệm tháng {month:02d}/{year}: Tổng thu {summary['total_income']:,.0f} đ, chi tiêu {summary['total_expense']:,.0f} đ. "
            + (prelim_text if summary["is_preliminary"] else f"Tỷ lệ tiết kiệm hiện đạt {summary['savings_rate']}%, cần tiếp tục tinh gọn chi tiêu không thiết yếu.")
            + budget_warning_text
        )
        trend_analysis = (
            (
                f"Danh mục chiếm tỷ trọng lớn nhất là '{summary['top_expenses'][0]['name']}' ({summary['top_expenses'][0]['amount']:,.0f} đ, chiếm {summary['top_expenses'][0]['percentage']}%). "
                if summary["top_expenses"]
                else "Chưa có đủ dữ liệu giao dịch chi tiêu để xác định danh mục hao tổn nhất. "
            )
            + ("Phát hiện bội chi ngân sách cần kiểm soát lại ngay." if summary["exceeded_budgets_count"] > 0 else "Việc kiểm soát chặt các khoản chi ngẫu hứng sẽ giúp nâng cao tỷ lệ thặng dư đáng kể.")
        )
        adjustments = [
            f"Cắt giảm khẩn cấp chi tiêu ở danh mục '{[b['category'] for b in summary['budgets'] if b['is_exceeded']][0]}' do đã vượt ngân sách."
            if summary["exceeded_budgets_count"] > 0
            else "Cắt giảm 10-15% chi tiêu ở danh mục chiếm tỷ trọng cao nhất trong tháng.",
            "Tạm hoãn các khoản mua sắm giải trí hoặc đồ dùng cá nhân chưa thực sự cấp thiết.",
            "Trích lập tự động tiền tiết kiệm ngay khi có nguồn thu nhập mới trước khi chi tiêu.",
        ]
        conclusion = "Kiên trì tối ưu từng khoản chi nhỏ sẽ tạo nên thặng dư tài chính vượt bậc theo thời gian!"
    elif focus == "risk":
        overview = (
            f"Báo cáo cảnh báo rủi ro tháng {month:02d}/{year}: Tổng thu {summary['total_income']:,.0f} đ, chi tiêu {summary['total_expense']:,.0f} đ. "
            + (prelim_text if summary["is_preliminary"] else f"Ghi nhận {summary['exceeded_budgets_count']} danh mục đã chạm hoặc vượt ngân sách đề ra.")
            + budget_warning_text
        )
        trend_analysis = (
            f"Mức chi biến động {summary['expense_growth_pct']:+.1f}% so với tháng trước. "
            + (
                f"Cảnh báo nghiêm trọng: Có {summary['exceeded_budgets_count']} hạn mức ngân sách bị vượt ngưỡng an toàn ({', '.join([b['category'] for b in summary['budgets'] if b['is_exceeded']])})."
                if summary["exceeded_budgets_count"] > 0
                else "Hệ thống chưa ghi nhận dấu hiệu bội chi bất thường ở các hạn mức ngân sách đã tạo."
            )
        )
        adjustments = [
            f"Khắc phục ngay tình trạng bội chi ở danh mục '{[b['category'] for b in summary['budgets'] if b['is_exceeded']][0]}' để tránh thâm hụt số dư."
            if summary["exceeded_budgets_count"] > 0
            else "Ưu tiên xây dựng quỹ dự phòng tài chính khẩn cấp tối thiểu từ 3 đến 6 tháng chi tiêu.",
            "Kích hoạt theo dõi sát các hạn mức ngân sách khi mức chi chạm ngưỡng 80%.",
            "Tránh phát sinh các khoản nợ tiêu dùng tín dụng mới trong giai đoạn thu chi chưa ổn định.",
        ]
        conclusion = "Bảo toàn thanh khoản và duy trì quỹ an toàn là tấm lá chắn tốt nhất trước mọi biến cố."
    else:  # comprehensive
        overview = (
            f"Trong tháng {month:02d}/{year}, tổng thu nhập đạt {summary['total_income']:,.0f} đ và chi tiêu {summary['total_expense']:,.0f} đ. "
            + (prelim_text if summary["is_preliminary"] else f"Tỷ lệ tiết kiệm đạt {summary['savings_rate']}%.")
            + budget_warning_text
        )
        trend_analysis = (
            f"Chi tiêu biến động {summary['expense_growth_pct']:+.1f}% so với tháng trước. "
            + (
                f"Danh mục chiếm tỷ trọng lớn nhất là '{summary['top_expenses'][0]['name']}' với {summary['top_expenses'][0]['amount']:,.0f} đ ({summary['top_expenses'][0]['percentage']}%)."
                if summary["top_expenses"]
                else "Chưa có đủ dữ liệu giao dịch chi tiêu lớn."
            )
            + (f" Có {summary['exceeded_budgets_count']} danh mục vượt ngân sách." if summary["exceeded_budgets_count"] > 0 else "")
        )
        adjustments = [
            f"Cắt giảm và chấn chỉnh chi tiêu danh mục '{[b['category'] for b in summary['budgets'] if b['is_exceeded']][0]}' do đã bội chi hạn mức."
            if summary["exceeded_budgets_count"] > 0
            else "Kiểm soát và cắt giảm các khoản chi tiêu không bắt buộc trong danh mục lớn nhất.",
            "Thiết lập hạn mức ngân sách đầu tháng cho từng nhóm nhu cầu thiết yếu.",
            "Trích tự động tối thiểu 15-20% thu nhập vào mục tiêu tiết kiệm ngay khi có nguồn thu mới.",
        ]
        conclusion = "Duy trì kỷ luật ghi chép giao dịch hàng ngày để kiểm soát dòng tiền hiệu quả hơn!"

    # Allow custom model resolver or fallback to genai.GenerativeModel
    from app.core.ai.gemini_client import get_gemini_model
    model_resolver = get_model_fn or get_gemini_model
    model = model_resolver()

    import app.core.ai_service as ai_service
    # Use ai_service.genai if patched, or genai
    active_genai = getattr(ai_service, "genai", genai)
    if model and active_genai:
        candidate_models = [
            settings.GEMINI_MODEL,
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-3.7-flash",
        ]
        candidate_models = list(dict.fromkeys(candidate_models))
        for mod_name in candidate_models:
            try:
                m = active_genai.GenerativeModel(
                    mod_name,
                    system_instruction=FOCUS_SYSTEM_INSTRUCTIONS.get(focus, SYSTEM_REPORT_PROMPT),
                    generation_config=active_genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=1500,
                    ),
                )
                res = await asyncio.wait_for(m.generate_content_async(user_prompt), timeout=10.0)
                if res and res.text:
                    cleaned_text = res.text.strip()
                    if "```" in cleaned_text:
                        cleaned_text = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_text)
                        cleaned_text = re.sub(r"\n?```$", "", cleaned_text).strip()
                    parsed = json.loads(cleaned_text)
                    if isinstance(parsed, dict):
                        overview = parsed.get("overview", overview)
                        trend_analysis = parsed.get("trend_analysis", trend_analysis)
                        if isinstance(parsed.get("adjustments"), list) and len(parsed["adjustments"]) >= 1:
                            adjustments = [str(x) for x in parsed["adjustments"][:3]]
                        conclusion = parsed.get("conclusion", conclusion)
                        break
            except Exception:
                continue

    focus_titles = {
        "comprehensive": "Phân Tích Toàn Diện",
        "saving": "Tối Ưu Tiết Kiệm",
        "risk": "Cảnh Báo Rủi Ro & An Toàn",
    }
    focus_label = focus_titles.get(focus, "Phân Tích Toàn Diện")

    raw_markdown = (
        f"# Báo Cáo Phân Tích Chi Tiêu Tháng {month:02d}/{year} ({focus_label})\n\n"
        f"**Sức khỏe tài chính:** {summary['health_status']} ({summary['health_score']}/100)\n"
        f"**Tích lũy vào mục tiêu tiết kiệm:** {summary['total_saving_deposited']:,.0f} đ ({summary['active_goals_count']} mục tiêu đang chạy)\n\n"
        f"### 1. Tổng Quan\n{overview}\n\n"
        f"### 2. Xu Hướng & Cơ Cấu Chi Tiêu\n{trend_analysis}\n\n"
        f"### 3. 3 Điểm Khuyến Nghị Cần Điều Chỉnh\n"
        + "\n".join([f"- **Điểm {idx+1}:** {adj}" for idx, adj in enumerate(adjustments)])
        + f"\n\n### 4. Kết Luận\n{conclusion}\n"
    )

    try:
        log_entry = AIReport(
            user_id=user_id,
            report_type=ReportType.MONTHLY_SUMMARY,
            prompt_sent=mask_sensitive_data(user_prompt),
            ai_response=raw_markdown,
            period_month=month,
            period_year=year,
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()

    # Dynamic applied_benchmarks are provided by retrieve_contextual_report_knowledge
    _legacy_benchmarks = [
        "VnExpress: Quy tắc quản lý tài chính 50/30/20 (https://vnexpress.net/quan-ly-tien-bang-quy-tac-50-30-20-4282825.html)",
        "VnExpress: Khung tiêu chuẩn Sức khỏe tài chính & Quỹ dự phòng 3-6 tháng (https://vnexpress.net/can-de-danh-bao-nhieu-tien-phong-than-4908291.html)",
    ]
    if focus == "saving":
        _legacy_benchmarks.append(
            "Báo Dân Trí: Nguyên tắc kiểm soát chi tiêu ngẫu hứng - Trì hoãn 24 Giờ (https://dantri.com.vn/kinh-doanh/meo-don-gian-giup-ban-tranh-mua-sam-boc-dong-giu-tien-trong-tui-20260725083137900.htm)"
        )

    if not applied_benchmarks:
        applied_benchmarks = _legacy_benchmarks

    return MonthlyReportResponse(
        month=f"{year:04d}-{month:02d}",
        financial_health_score=summary["health_score"],
        health_status=summary["health_status"],
        total_income=summary["total_income"],
        total_expense=summary["total_expense"],
        net_savings=summary["net_savings"],
        savings_rate=summary["savings_rate"],
        overview=overview,
        trend_analysis=trend_analysis,
        top_categories=summary["top_expenses"][:5],
        adjustments=adjustments,
        conclusion=conclusion,
        raw_markdown=raw_markdown,
        generated_at=datetime.now(timezone.utc),
        focus=focus,
        total_saving_deposited=summary["total_saving_deposited"],
        active_goals_count=summary["active_goals_count"],
        rag_benchmarks=applied_benchmarks,
    )
