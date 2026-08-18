"""Core AI and Financial Trend Analytics Service.

Implements monthly trend aggregation, structured AI monthly reports according to
REQUIREMENTS.md specifications, smart budget recommendations, and PII masking.
"""

import asyncio
import calendar
import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import google.generativeai as genai
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.ai_chat import mask_sensitive_data
from app.models.ai_report import AIReport
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType, ReportType
from app.models.transaction import Transaction
from app.schemas.ai import (
    ApplyRecommendationItem,
    BudgetRecommendationItem,
    BudgetRecommendationResponse,
    CategoryAnomalyItem,
    MonthlyReportResponse,
    MonthlyTrendItem,
    MonthlyTrendResponse,
    SpendingPredictionData,
    SpendingVelocityItem,
)

SYSTEM_REPORT_PROMPT = (
    "Bạn là trợ lý chi tiêu cá nhân. Chỉ đưa gợi ý tham khảo, không tư vấn tài chính chuyên nghiệp."
)


def _get_gemini_model(system_instruction: str = SYSTEM_REPORT_PROMPT):
    """Initialize Gemini GenerativeModel if configured."""
    if not settings.GEMINI_API_KEY:
        return None
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        settings.GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=1500,
        ),
    )


# ---------------------------------------------------------------------------
# 1. Monthly Trend Aggregation
# ---------------------------------------------------------------------------


def get_monthly_trend_data(
    db: Session, user_id: int, months: int = 6
) -> MonthlyTrendResponse:
    """Aggregate financial trends over the past N months for a user."""
    today = date.today()
    months = max(1, min(months, 24))

    # Calculate month slots in chronological order: [N-1 months ago, ..., current month]
    month_slots: list[tuple[int, int]] = []
    curr_y, curr_m = today.year, today.month
    for i in range(months - 1, -1, -1):
        target_m = curr_m - i
        target_y = curr_y
        while target_m <= 0:
            target_m += 12
            target_y -= 1
        month_slots.append((target_y, target_m))

    start_y, start_m = month_slots[0]
    start_date = date(start_y, start_m, 1)
    end_y, end_m = month_slots[-1]
    last_day = calendar.monthrange(end_y, end_m)[1]
    end_date = date(end_y, end_m, last_day)

    # Query transactions within the date range
    txns = (
        db.query(
            Transaction.transaction_date,
            Transaction.type,
            Transaction.amount,
            Category.name.label("category_name"),
        )
        .outerjoin(
            Category,
            (Transaction.category_id == Category.id)
            & (Transaction.user_id == Category.user_id),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .all()
    )

    data_map: dict[tuple[int, int], dict[str, Decimal]] = {
        slot: {"income": Decimal("0.00"), "expense": Decimal("0.00")}
        for slot in month_slots
    }
    top_cat_map_aggs: dict[tuple[int, int], dict[str, Decimal]] = {
        slot: {} for slot in month_slots
    }

    for txn_date, txn_type, total, cat_name in txns:
        if not txn_date:
            continue
        slot = (txn_date.year, txn_date.month)
        if slot in data_map:
            amount = Decimal(str(total or 0)).quantize(Decimal("0.01"))
            if txn_type == CategoryType.INCOME or txn_type == CategoryType.INCOME.value or str(txn_type).lower() == "income":
                data_map[slot]["income"] += amount
            else:
                data_map[slot]["expense"] += amount
                if cat_name:
                    top_cat_map_aggs[slot][cat_name] = (
                        top_cat_map_aggs[slot].get(cat_name, Decimal("0.00")) + amount
                    )

    items: list[MonthlyTrendItem] = []
    total_income_all = Decimal("0.00")
    total_expense_all = Decimal("0.00")

    for slot in month_slots:
        y, m = slot
        inc = data_map[slot]["income"]
        exp = data_map[slot]["expense"]
        net = inc - exp
        savings_pct = (
            round(float((net / inc) * 100), 1) if inc > Decimal("0.00") else 0.0
        )
        cat_aggs = top_cat_map_aggs.get(slot, {})
        if cat_aggs:
            top_cat, top_cat_amt = max(cat_aggs.items(), key=lambda x: x[1])
        else:
            top_cat, top_cat_amt = (None, None)

        total_income_all += inc
        total_expense_all += exp

        items.append(
            MonthlyTrendItem(
                month=f"{y:04d}-{m:02d}",
                year=y,
                month_num=m,
                label=f"Thg {m:02d}/{y}",
                total_income=inc,
                total_expense=exp,
                net_savings=net,
                savings_rate=savings_pct,
                top_category=top_cat,
                top_category_amount=top_cat_amt,
            )
        )

    count = len(items) or 1
    avg_income = (total_income_all / count).quantize(Decimal("0.01"))
    avg_expense = (total_expense_all / count).quantize(Decimal("0.01"))
    avg_savings = avg_income - avg_expense
    avg_savings_rate = (
        round(float((avg_savings / avg_income) * 100), 1)
        if avg_income > Decimal("0.00")
        else 0.0
    )

    # -----------------------------------------------------------------------
    # 1.1. Spending Velocity & Ideal Line for Current Month
    # -----------------------------------------------------------------------
    days_in_current_month = calendar.monthrange(curr_y, curr_m)[1]
    days_passed = min(today.day, days_in_current_month)

    user_budgets = (
        db.query(Budget)
        .filter(
            Budget.user_id == user_id,
            Budget.month == curr_m,
            Budget.year == curr_y,
        )
        .all()
    )
    total_budget_curr = sum(
        (Decimal(str(b.amount or 0)) for b in user_budgets), Decimal("0.00")
    )

    daily_txns = (
        db.query(
            Transaction.transaction_date,
            sa_func.coalesce(sa_func.sum(Transaction.amount), 0).label("daily_total"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.type == CategoryType.EXPENSE,
            Transaction.transaction_date >= date(curr_y, curr_m, 1),
            Transaction.transaction_date <= date(curr_y, curr_m, days_in_current_month),
        )
        .group_by(Transaction.transaction_date)
        .all()
    )
    daily_spend_map = {
        t_date.day: Decimal(str(d_tot or 0)).quantize(Decimal("0.01"))
        for t_date, d_tot in daily_txns
        if t_date
    }

    ideal_baseline = total_budget_curr if total_budget_curr > 0 else avg_expense
    ideal_daily_rate = (
        (ideal_baseline / Decimal(str(days_in_current_month))).quantize(Decimal("0.01"))
        if ideal_baseline > 0
        else Decimal("0.00")
    )

    velocity_items: list[SpendingVelocityItem] = []
    running_spend = Decimal("0.00")
    for d in range(1, days_in_current_month + 1):
        is_past_or_today = d <= days_passed
        day_spend = daily_spend_map.get(d, Decimal("0.00"))
        if is_past_or_today:
            running_spend += day_spend
            cumul = running_spend
        else:
            cumul = Decimal("0.00")

        ideal = (ideal_daily_rate * Decimal(str(d))).quantize(Decimal("0.01"))
        velocity_items.append(
            SpendingVelocityItem(
                day=d,
                date_str=f"{d:02d}/{curr_m:02d}",
                cumulative_spend=cumul if is_past_or_today else Decimal("0.00"),
                ideal_spend=ideal,
                actual_daily_spend=day_spend if is_past_or_today else Decimal("0.00"),
            )
        )

    # -----------------------------------------------------------------------
    # 1.2. Predictive End-of-Month Runrate
    # -----------------------------------------------------------------------
    current_spent = running_spend
    burn_rate = (
        current_spent / Decimal(str(max(1, days_passed)))
    ).quantize(Decimal("0.01"))
    projected_end = (burn_rate * Decimal(str(days_in_current_month))).quantize(
        Decimal("0.01")
    )
    projected_diff = (
        projected_end - total_budget_curr if total_budget_curr > 0 else Decimal("0.00")
    )
    is_overrun = total_budget_curr > 0 and projected_end > total_budget_curr
    risk_level = (
        "danger"
        if (total_budget_curr > 0 and projected_end > total_budget_curr * Decimal("1.10"))
        else "warning"
        if is_overrun
        else "safe"
    )

    curr_income = data_map.get((curr_y, curr_m), {}).get("income", Decimal("0.00"))
    proj_savings_rate = (
        round(float(((curr_income - projected_end) / curr_income) * 100), 1)
        if curr_income > Decimal("0.00")
        else 0.0
    )

    prediction_data = SpendingPredictionData(
        current_spent=current_spent,
        total_budget=total_budget_curr,
        days_passed=days_passed,
        total_days=days_in_current_month,
        daily_burn_rate=burn_rate,
        projected_end_month_spend=projected_end,
        projected_diff_amount=projected_diff,
        is_overrun_risk=is_overrun,
        risk_level=risk_level,
        projected_savings_rate=proj_savings_rate,
    )

    # -----------------------------------------------------------------------
    # 1.3. Anomaly Surge Detection (vs 3-month rolling average)
    # -----------------------------------------------------------------------
    prior_3_slots: list[tuple[int, int]] = []
    for j in range(1, 4):
        pm = curr_m - j
        py = curr_y
        while pm <= 0:
            pm += 12
            py -= 1
        prior_3_slots.append((py, pm))

    oldest_slot = prior_3_slots[-1]
    cat_txns = (
        db.query(
            Transaction.transaction_date,
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
            Transaction.amount,
        )
        .join(
            Category,
            (Transaction.category_id == Category.id)
            & (Transaction.user_id == Category.user_id),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.type == CategoryType.EXPENSE,
            Transaction.transaction_date >= date(oldest_slot[0], oldest_slot[1], 1),
            Transaction.transaction_date <= date(curr_y, curr_m, days_in_current_month),
        )
        .all()
    )

    current_cat_map: dict[int, dict[str, Any]] = {}
    prior_cat_map: dict[int, list[Decimal]] = {}
    for t_date, c_id, c_name, c_icon, c_color, amt in cat_txns:
        if not t_date or not c_id:
            continue
        slot = (t_date.year, t_date.month)
        val = Decimal(str(amt or 0)).quantize(Decimal("0.01"))
        if slot == (curr_y, curr_m):
            if c_id not in current_cat_map:
                current_cat_map[c_id] = {
                    "id": c_id,
                    "name": c_name or "Khác",
                    "icon": c_icon,
                    "color": c_color,
                    "amount": Decimal("0.00"),
                }
            current_cat_map[c_id]["amount"] += val
        elif slot in prior_3_slots:
            if c_id not in prior_cat_map:
                prior_cat_map[c_id] = []
            prior_cat_map[c_id].append(val)

    anomaly_items: list[CategoryAnomalyItem] = []
    for c_id, info in current_cat_map.items():
        cur_amt = info["amount"]
        p_list = prior_cat_map.get(c_id, [])
        avg_3m = (
            (sum(p_list, Decimal("0.00")) / Decimal("3")).quantize(Decimal("0.01"))
            if p_list
            else Decimal("0.00")
        )
        if avg_3m > Decimal("0.00"):
            diff_pct = round(float(((cur_amt - avg_3m) / avg_3m) * 100), 1)
            diff_amt = cur_amt - avg_3m
        else:
            diff_pct = 100.0 if cur_amt > Decimal("0.00") else 0.0
            diff_amt = cur_amt

        is_spike = diff_pct >= 30.0 and diff_amt >= Decimal("100000.00")
        if is_spike:
            anomaly_items.append(
                CategoryAnomalyItem(
                    category_id=c_id,
                    category_name=info["name"],
                    category_icon=info["icon"],
                    category_color=info["color"],
                    current_month_amount=cur_amt,
                    avg_3m_amount=avg_3m,
                    diff_percent=diff_pct,
                    diff_amount=diff_amt,
                    is_spike=True,
                    note=f"Tăng {diff_pct:+0.1f}% so với trung bình 3 tháng gần nhất",
                )
            )

    anomaly_items.sort(key=lambda x: x.diff_amount, reverse=True)

    # -----------------------------------------------------------------------
    # 1.4. Smart Executive Text Summary & Actionable Recommendations
    # -----------------------------------------------------------------------
    prev_slot = (curr_y, curr_m - 1) if curr_m > 1 else (curr_y - 1, 12)
    prev_exp = data_map.get(prev_slot, {}).get("expense", Decimal("0.00"))
    curr_exp = data_map.get((curr_y, curr_m), {}).get("expense", Decimal("0.00"))

    summary_parts = []
    if prev_exp > Decimal("0.00") and curr_exp > Decimal("0.00"):
        exp_diff_pct = round(float(((curr_exp - prev_exp) / prev_exp) * 100), 1)
        if exp_diff_pct < 0:
            summary_parts.append(
                f"Tháng này bạn đang chi tiêu chậm hơn {abs(exp_diff_pct)}% so với cùng kỳ tháng trước."
            )
        elif exp_diff_pct > 0:
            summary_parts.append(
                f"Tháng này chi tiêu đang tăng {exp_diff_pct}% so với tháng trước."
            )
        else:
            summary_parts.append("Mức chi tiêu tháng này tương đương tháng trước.")
    else:
        summary_parts.append(f"Tổng quan xu hướng {len(items)} tháng gần nhất được tổng hợp đầy đủ.")

    if is_overrun:
        summary_parts.append(
            f"Cảnh báo: Với tốc độ chi tiêu hiện tại, dự kiến cuối tháng có nguy cơ vượt hạn mức ngân sách."
        )
    else:
        summary_parts.append(
            f"Tỷ lệ tiết kiệm trung bình đạt {avg_savings_rate}%, dòng tiền duy trì mức an toàn."
        )

    smart_summary = " ".join(summary_parts)

    insights: list[str] = []
    if anomaly_items:
        top_sp = anomaly_items[0]
        insights.append(
            f"Danh mục '{top_sp.category_name}' tăng đột biến +{top_sp.diff_percent}%. Hãy kiểm soát các khoản chi phát sinh trong thời gian tới."
        )
    if is_overrun:
        insights.append(
            "Tốc độ tiêu tiền lũy kế đang cao hơn đường ngân sách lý tưởng. Nên giảm nhẹ các khoản chi không thiết yếu."
        )
    if avg_savings_rate >= 25.0:
        insights.append(
            f"Bạn duy trì tỷ lệ tiết kiệm rất tốt ({avg_savings_rate}%). Có thể trích một phần vào Mục tiêu tiết kiệm để tích lũy tài sản."
        )
    elif avg_savings_rate < 10.0 and avg_income > Decimal("0.00"):
        insights.append(
            "Tỷ lệ tiết kiệm đang ở mức thấp (< 10%). Hãy rà soát lại các khoản định phí để tăng thặng dư tích lũy."
        )
    if not insights:
        insights.append(
            "Hãy duy trì ghi chép giao dịch đều đặn để hệ thống dự báo dòng tiền chính xác hơn."
        )

    return MonthlyTrendResponse(
        months_count=len(items),
        items=items,
        average_monthly_income=avg_income,
        average_monthly_expense=avg_expense,
        average_monthly_savings=avg_savings,
        average_savings_rate=avg_savings_rate,
        smart_summary=smart_summary,
        actionable_insights=insights,
        velocity_data=velocity_items,
        prediction_data=prediction_data,
        anomaly_items=anomaly_items,
    )


# ---------------------------------------------------------------------------
# 2. AI Monthly Report Generator
# ---------------------------------------------------------------------------


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
        # Find spent
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

    # 5. Baseline Financial Health Score calculation (0 - 100)
    score = 70  # Base
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
        "health_score": score,
        "health_status": health_status,
    }


async def generate_monthly_ai_report(
    db: Session, user_id: int, month_str: str
) -> MonthlyReportResponse:
    """Generate an AI monthly spending report adhering to REQUIREMENTS.md."""
    try:
        parts = month_str.split("-")
        year = int(parts[0])
        month = int(parts[1])
    except (ValueError, IndexError):
        year, month = date.today().year, date.today().month

    summary = calculate_monthly_financial_summary(db, user_id, year, month)

    # Build {{monthly_expense_summary}} payload as required by section 5 of REQUIREMENTS.md
    top_exp_lines = [
        f"- {e['name']}: {e['amount']:,.0f} đ ({e['percentage']}%)"
        for e in summary["top_expenses"][:5]
    ]
    summary_text = (
        f"Tháng: {month:02d}/{year}\n"
        f"Tổng thu nhập: {summary['total_income']:,.0f} VNĐ\n"
        f"Tổng chi tiêu: {summary['total_expense']:,.0f} VNĐ\n"
        f"Tiết kiệm thặng dư: {summary['net_savings']:,.0f} VNĐ (Tỷ lệ: {summary['savings_rate']}%)\n"
        f"So với tháng trước ({summary['prev_expense']:,.0f} VNĐ): Biến động {summary['expense_growth_pct']:+.1f}%\n"
        f"Top danh mục chi tiêu:\n" + ("\n".join(top_exp_lines) if top_exp_lines else "Chưa có giao dịch chi tiêu.")
    )

    # Prompt specified in REQUIREMENTS.md:
    # User: Dữ liệu chi tiêu tháng: {{monthly_expense_summary}}. Hãy tóm tắt xu hướng và gợi ý 3 điểm cần điều chỉnh.
    user_prompt = (
        f"Dữ liệu chi tiêu tháng:\n{summary_text}\n\n"
        f"Hãy tóm tắt xu hướng và gợi ý 3 điểm cần điều chỉnh.\n\n"
        f"Trả lời dưới định dạng JSON với cấu trúc sau:\n"
        f"{{\n"
        f'  "overview": "Tóm tắt tổng quan tình hình tài chính tháng này trong 1-2 câu",\n'
        f'  "trend_analysis": "Phân tích cụ thể xu hướng thu/chi, so sánh với tháng trước và danh mục chi tiêu lớn nhất",\n'
        f'  "adjustments": [\n'
        f'    "Gợi ý điều chỉnh hành động 1 (cụ thể, thiết thực)",\n'
        f'    "Gợi ý điều chỉnh hành động 2 (cụ thể, thiết thực)",\n'
        f'    "Gợi ý điều chỉnh hành động 3 (cụ thể, thiết thực)"\n'
        f"  ],\n"
        f'  "conclusion": "Lời khuyên đúc kết tài chính ngắn gọn và động lực tiết kiệm cho tháng tới"\n'
        f"}}"
    )

    overview = (
        f"Trong tháng {month}/{year}, tổng thu nhập đạt {summary['total_income']:,.0f} đ và chi tiêu {summary['total_expense']:,.0f} đ, "
        f"đạt tỷ lệ tiết kiệm {summary['savings_rate']}%."
    )
    trend_analysis = (
        f"Chi tiêu biến động {summary['expense_growth_pct']:+.1f}% so với tháng trước. "
        + (
            f"Danh mục chiếm tỷ trọng lớn nhất là '{summary['top_expenses'][0]['name']}' với {summary['top_expenses'][0]['amount']:,.0f} đ ({summary['top_expenses'][0]['percentage']}%)."
            if summary["top_expenses"]
            else "Chưa có đủ dữ liệu giao dịch chi tiêu lớn."
        )
    )
    adjustments = [
        "Kiểm soát và cắt giảm các khoản chi tiêu không bắt buộc trong danh mục lớn nhất.",
        "Thiết lập hạn mức ngân sách đầu tháng cho từng nhóm nhu cầu thiết yếu.",
        "Trích tự động tối thiểu 15-20% thu nhập vào mục tiêu tiết kiệm ngay khi có nguồn thu mới.",
    ]
    conclusion = "Duy trì kỷ luật ghi chép giao dịch hàng ngày để kiểm soát dòng tiền hiệu quả hơn!"

    model = _get_gemini_model()
    if model:
        candidate_models = [
            settings.GEMINI_MODEL,
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-flash-latest",
        ]
        candidate_models = list(dict.fromkeys(candidate_models))
        for mod_name in candidate_models:
            try:
                m = genai.GenerativeModel(
                    mod_name,
                    system_instruction=SYSTEM_REPORT_PROMPT,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=1500,
                    ),
                )
                res = await asyncio.wait_for(m.generate_content_async(user_prompt), timeout=10.0)
                if res and res.text:
                    cleaned_text = res.text.strip()
                    # Strip ```json if present
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

    # Compose markdown document
    raw_markdown = (
        f"# Báo Cáo Phân Tích Chi Tiêu Tháng {month:02d}/{year}\n\n"
        f"**Sức khỏe tài chính:** {summary['health_status']} ({summary['health_score']}/100)\n\n"
        f"### 1. Tổng Quan\n{overview}\n\n"
        f"### 2. Xu Hướng & Cơ Cấu Chi Tiêu\n{trend_analysis}\n\n"
        f"### 3. 3 Điểm Khuyến Nghị Cần Điều Chỉnh\n"
        + "\n".join([f"- **Điểm {idx+1}:** {adj}" for idx, adj in enumerate(adjustments)])
        + f"\n\n### 4. Kết Luận\n{conclusion}\n"
    )
    # Save AIReport log in database
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
    )


# ---------------------------------------------------------------------------
# 3. AI Budget Recommendations
# ---------------------------------------------------------------------------


async def generate_budget_recommendations(
    db: Session, user_id: int, target_month: int, target_year: int
) -> BudgetRecommendationResponse:
    """Generate smart budget recommendations for active expense categories based on 1-3 month history."""
    # 1. Fetch all active expense categories of user
    categories = (
        db.query(Category)
        .filter(
            Category.user_id == user_id,
            Category.type.in_([CategoryType.EXPENSE, CategoryType.EXPENSE.value, "expense"]),
            Category.deleted_at.is_(None),
            Category.is_active.is_(True),
        )
        .order_by(Category.name.asc())
        .all()
    )

    if not categories:
        return BudgetRecommendationResponse(
            target_month=target_month,
            target_year=target_year,
            total_recommended=Decimal("0.00"),
            recommendations=[],
        )

    # 2. Calculate historical spend for past 3 months up to target month
    first_hist_date = date(target_year, target_month, 1) - timedelta(days=95)
    start_hist = date(first_hist_date.year, first_hist_date.month, 1)
    last_day_target = calendar.monthrange(target_year, target_month)[1]
    end_hist = date(target_year, target_month, last_day_target)

    hist_txns = (
        db.query(
            Transaction.category_id,
            Transaction.transaction_date,
            Transaction.amount,
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.type.in_([CategoryType.EXPENSE, CategoryType.EXPENSE.value, "expense"]),
            Transaction.transaction_date >= start_hist,
            Transaction.transaction_date <= end_hist,
        )
        .all()
    )

    cat_history_map: dict[tuple[int, int, int], Decimal] = {}
    last_month_num = target_month - 1 if target_month > 1 else 12
    last_month_yr = target_year if target_month > 1 else target_year - 1
    last_month_spend_map: dict[int, Decimal] = {c.id: Decimal("0.00") for c in categories}
    current_month_spend_map: dict[int, Decimal] = {c.id: Decimal("0.00") for c in categories}

    for cat_id, txn_date, amount in hist_txns:
        if not cat_id or not txn_date:
            continue
        amt = Decimal(str(amount or 0)).quantize(Decimal("0.01"))
        key = (cat_id, txn_date.year, txn_date.month)
        cat_history_map[key] = cat_history_map.get(key, Decimal("0.00")) + amt
        if txn_date.year == last_month_yr and txn_date.month == last_month_num:
            last_month_spend_map[cat_id] = last_month_spend_map.get(cat_id, Decimal("0.00")) + amt
        if txn_date.year == target_year and txn_date.month == target_month:
            current_month_spend_map[cat_id] = current_month_spend_map.get(cat_id, Decimal("0.00")) + amt

    cat_history: dict[int, list[Decimal]] = {c.id: [] for c in categories}
    for (cat_id, yr, mo), monthly_total in cat_history_map.items():
        if cat_id in cat_history:
            cat_history[cat_id].append(monthly_total)

    # Prepare prompt data
    prompt_items = []
    default_recs: list[BudgetRecommendationItem] = []
    total_rec = Decimal("0.00")

    for cat in categories:
        history = cat_history[cat.id]
        avg_spent = (
            (sum(history) / len(history)).quantize(Decimal("0.01"))
            if history
            else Decimal("0.00")
        )
        last_spent = last_month_spend_map[cat.id]
        curr_spent = current_month_spend_map[cat.id]

        # Rule-based default: round to nearest 50,000 VNĐ, with 5% buffer if has history, or default 500,000
        if avg_spent > Decimal("0.00"):
            base_amount = int(avg_spent * Decimal("1.05"))
            rec_amount = Decimal((base_amount // 50000 + 1) * 50000).quantize(
                Decimal("0.01")
            )
            reason = f"Dựa trên mức chi trung bình {avg_spent:,.0f} đ gần đây kèm mức dự phòng 5%."
        elif last_spent > Decimal("0.00"):
            base_amount = int(last_spent * Decimal("1.05"))
            rec_amount = Decimal((base_amount // 50000 + 1) * 50000).quantize(
                Decimal("0.01")
            )
            reason = f"Dựa trên mức chi {last_spent:,.0f} đ của tháng trước."
        elif curr_spent > Decimal("0.00"):
            base_amount = int(curr_spent * Decimal("1.2"))
            rec_amount = Decimal((base_amount // 50000 + 1) * 50000).quantize(
                Decimal("0.01")
            )
            reason = f"Dựa trên mức chi {curr_spent:,.0f} đ hiện tại trong tháng."
        else:
            rec_amount = Decimal("500000.00")
            reason = "Hạn mức đề xuất khởi đầu cho danh mục mới."

        total_rec += rec_amount
        rec_item = BudgetRecommendationItem(
            category_id=cat.id,
            category_name=cat.name,
            category_icon=cat.icon,
            category_color=cat.color,
            avg_spent=avg_spent,
            last_month_spent=last_spent,
            recommended_amount=rec_amount,
            reason=reason,
        )
        default_recs.append(rec_item)
        prompt_items.append({
            "id": cat.id,
            "name": cat.name,
            "avg_spent": float(avg_spent),
            "last_spent": float(last_spent),
        })

    # Prompt Gemini for AI-refined reasons and amounts
    model = _get_gemini_model(
        system_instruction="Bạn là trợ lý tài chính cá nhân thông minh. Đưa ra gợi ý hạn mức ngân sách hàng tháng hợp lý, thực tế và tiết kiệm."
    )
    if model and prompt_items:
        prompt = (
            f"Dưới đây là danh sách các danh mục chi tiêu của người dùng cho tháng {target_month:02d}/{target_year} kèm mức chi trung bình (avg_spent) và tháng trước (last_spent):\n"
            f"{json.dumps(prompt_items, ensure_ascii=False, indent=2)}\n\n"
            f"Hãy đưa ra mức ngân sách đề xuất (recommended_amount dạng số làm tròn đến 10,000 hoặc 50,000 VNĐ) và lý do ngắn gọn (reason trong 1 câu tiếng Việt).\n"
            f"Trả về kết quả dưới dạng JSON array: [{{ 'id': <category_id>, 'recommended_amount': <number>, 'reason': '<lý do ngắn gọn>' }}]"
        )
        try:
            res = await asyncio.wait_for(model.generate_content_async(prompt), timeout=8.0)
            if res and res.text:
                cleaned = res.text.strip()
                if "```" in cleaned:
                    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
                    cleaned = re.sub(r"\n?```$", "", cleaned).strip()
                ai_list = json.loads(cleaned)
                if isinstance(ai_list, list):
                    ai_map = {item.get("id"): item for item in ai_list if isinstance(item, dict)}
                    updated_recs = []
                    new_total = Decimal("0.00")
                    for rec in default_recs:
                        if rec.category_id in ai_map:
                            ai_item = ai_map[rec.category_id]
                            ai_amt = ai_item.get("recommended_amount")
                            if ai_amt and isinstance(ai_amt, (int, float)) and ai_amt > 0:
                                rec.recommended_amount = Decimal(str(ai_amt)).quantize(Decimal("0.01"))
                            if ai_item.get("reason"):
                                rec.reason = str(ai_item.get("reason"))
                        new_total += rec.recommended_amount
                        updated_recs.append(rec)
                    return BudgetRecommendationResponse(
                        target_month=target_month,
                        target_year=target_year,
                        total_recommended=new_total,
                        recommendations=updated_recs,
                    )
        except Exception:
            pass

    return BudgetRecommendationResponse(
        target_month=target_month,
        target_year=target_year,
        total_recommended=total_rec,
        recommendations=default_recs,
    )


# ---------------------------------------------------------------------------
# 4. Apply Budget Recommendations
# ---------------------------------------------------------------------------


def apply_budget_recommendations(
    db: Session,
    user_id: int,
    target_month: int,
    target_year: int,
    recommendations: list[ApplyRecommendationItem],
) -> tuple[int, str]:
    """Apply a list of budget recommendations for target month/year."""
    applied_count = 0

    for item in recommendations:
        # Validate category ownership and validity
        cat = (
            db.query(Category)
            .filter(
                Category.id == item.category_id,
                Category.user_id == user_id,
                Category.deleted_at.is_(None),
                Category.type.in_([CategoryType.EXPENSE, CategoryType.EXPENSE.value, "expense"]),
            )
            .first()
        )
        if not cat:
            continue

        existing_budget = (
            db.query(Budget)
            .filter(
                Budget.user_id == user_id,
                Budget.category_id == item.category_id,
                Budget.month == target_month,
                Budget.year == target_year,
            )
            .first()
        )

        if existing_budget:
            existing_budget.amount = item.amount
        else:
            new_budget = Budget(
                user_id=user_id,
                category_id=item.category_id,
                amount=item.amount,
                month=target_month,
                year=target_year,
            )
            db.add(new_budget)

        applied_count += 1

    db.commit()
    return applied_count, f"Đã áp dụng thành công ngân sách cho {applied_count} danh mục trong tháng {target_month:02d}/{target_year}."
