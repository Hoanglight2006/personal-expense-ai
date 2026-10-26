"""Monthly financial trend aggregation and predictive analysis.

Calculates multi-month cash flow summaries, spending velocity vs ideal budget burn,
runrate end-of-month projection, and anomaly expense spikes.
"""

from __future__ import annotations

import calendar
from datetime import date
from app.core.timezone import local_today
from decimal import Decimal
from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.schemas.ai import (
    CategoryAnomalyItem,
    MonthlyTrendItem,
    MonthlyTrendResponse,
    SpendingPredictionData,
    SpendingVelocityItem,
)


def get_monthly_trend_data(
    db: Session, user_id: int, months: int = 6
) -> MonthlyTrendResponse:
    """Aggregate financial trends over the past N months for a user."""
    today = local_today()
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

    # 1.1. Spending Velocity & Ideal Line for Current Month
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

    # 1.2. Predictive End-of-Month Runrate
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

    # 1.3. Anomaly Surge Detection (vs 3-month rolling average)
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

    # 1.4. Smart Executive Text Summary & Actionable Recommendations
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
            "Cảnh báo: Với tốc độ chi tiêu hiện tại, dự kiến cuối tháng có nguy cơ vượt hạn mức ngân sách."
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
