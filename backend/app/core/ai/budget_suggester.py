"""Smart budget recommendation engine with Gemini AI suggestions and 1-click apply.
"""

from __future__ import annotations

import asyncio
import calendar
import json
import math
import re
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.prompts import format_prompt, get_prompt
from app.core.rag import retrieve_contextual_budget_knowledge
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.schemas.ai import (
    ApplyRecommendationItem,
    BudgetRecommendationItem,
    BudgetRecommendationResponse,
)


async def generate_budget_recommendations(
    db: Session,
    user_id: int,
    target_month: int,
    target_year: int,
    lookback_months: int = 3,
    get_model_fn=None,
) -> BudgetRecommendationResponse:
    """Generate smart budget recommendations for active expense categories based on prior N months history."""
    lookback_months = max(1, min(lookback_months, 12))

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
            rag_benchmarks=[],
        )

    # 1. Calculate prior N full calendar months strictly before target_month
    prior_slots: list[tuple[int, int]] = []
    for step in range(lookback_months, 0, -1):
        pm = target_month - step
        py = target_year
        while pm <= 0:
            pm += 12
            py -= 1
        prior_slots.append((py, pm))

    start_hist = date(prior_slots[0][0], prior_slots[0][1], 1)
    last_day_target = calendar.monthrange(target_year, target_month)[1]
    end_hist = date(target_year, target_month, last_day_target)

    hist_txns = (
        db.query(
            Transaction.category_id,
            Transaction.transaction_date,
            Transaction.amount,
            Transaction.type,
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= start_hist,
            Transaction.transaction_date <= end_hist,
        )
        .all()
    )

    cat_history_map: dict[tuple[int, int, int], Decimal] = {}
    last_slot = prior_slots[-1]
    last_month_spend_map: dict[int, Decimal] = {c.id: Decimal("0.00") for c in categories}
    current_month_spend_map: dict[int, Decimal] = {c.id: Decimal("0.00") for c in categories}
    income_monthly_map: dict[tuple[int, int], Decimal] = {}

    for cat_id, txn_date, amount, txn_type in hist_txns:
        if not txn_date or not amount:
            continue
        amt = Decimal(str(amount or 0)).quantize(Decimal("0.01"))
        month_key = (txn_date.year, txn_date.month)

        if txn_type in [CategoryType.INCOME, CategoryType.INCOME.value, "income"]:
            income_monthly_map[month_key] = income_monthly_map.get(month_key, Decimal("0.00")) + amt
        elif txn_type in [CategoryType.EXPENSE, CategoryType.EXPENSE.value, "expense"] and cat_id:
            key = (cat_id, txn_date.year, txn_date.month)
            cat_history_map[key] = cat_history_map.get(key, Decimal("0.00")) + amt
            if (txn_date.year, txn_date.month) == last_slot:
                last_month_spend_map[cat_id] = last_month_spend_map.get(cat_id, Decimal("0.00")) + amt
            if txn_date.year == target_year and txn_date.month == target_month:
                current_month_spend_map[cat_id] = current_month_spend_map.get(cat_id, Decimal("0.00")) + amt

    active_incomes = [v for v in income_monthly_map.values() if v > Decimal("0.00")]
    if active_incomes:
        avg_monthly_income = (sum(active_incomes) / Decimal(str(len(active_incomes)))).quantize(Decimal("0.01"))
    else:
        avg_monthly_income = Decimal("0.00")

    today = date.today()
    is_target_current_month = (target_year == today.year and target_month == today.month)
    days_in_target_month = calendar.monthrange(target_year, target_month)[1]
    days_passed = max(1, today.day) if is_target_current_month else days_in_target_month

    # Data Maturity & Sufficiency Criteria
    MIN_INCOME_FLOOR = Decimal("2000000.00")  # Minimum monthly income to reflect viable full-month living
    MIN_TXN_COUNT_RELIABLE = 5
    MIN_SPAN_DAYS_RELIABLE = 7

    expense_txns = [
        t for t in hist_txns
        if t[3] in [CategoryType.EXPENSE, CategoryType.EXPENSE.value, "expense"] and (t[2] or 0) > 0
    ]
    total_expense_txn_count = len(expense_txns)
    distinct_expense_dates = {t[1] for t in expense_txns if t[1]}
    if distinct_expense_dates:
        date_span_days = (max(distinct_expense_dates) - min(distinct_expense_dates)).days + 1
    else:
        date_span_days = 0

    # Count how many prior months have significant data (at least 3 txns or >= 1m VND spent)
    qualified_prior_months = 0
    for y, m in prior_slots:
        m_txns = [t for t in expense_txns if t[1] and t[1].year == y and t[1].month == m]
        m_spent = sum(Decimal(str(t[2] or 0)) for t in m_txns)
        if len(m_txns) >= 3 or m_spent >= Decimal("1000000.00"):
            qualified_prior_months += 1

    is_data_sufficient = (
        (qualified_prior_months >= 1) or
        (total_expense_txn_count >= MIN_TXN_COUNT_RELIABLE and date_span_days >= MIN_SPAN_DAYS_RELIABLE)
    )
    is_income_sufficient = (avg_monthly_income >= MIN_INCOME_FLOOR)

    def _get_standard_baseline(cat_name_l: str) -> Decimal:
        if any(k in cat_name_l for k in ["ăn", "food", "uống", "dining"]):
            return Decimal("2500000.00")
        elif any(k in cat_name_l for k in ["nhà", "phòng", "home", "rent", "trọ"]):
            return Decimal("2000000.00")
        elif any(k in cat_name_l for k in ["đi lại", "di chuyển", "xăng", "xe", "transport"]):
            return Decimal("500000.00")
        elif any(k in cat_name_l for k in ["mua sắm", "shopping"]):
            return Decimal("500000.00")
        elif any(k in cat_name_l for k in ["giải trí", "entertainment", "chơi"]):
            return Decimal("400000.00")
        elif any(k in cat_name_l for k in ["giáo dục", "học", "sách", "education"]):
            return Decimal("300000.00")
        elif any(k in cat_name_l for k in ["y tế", "sức khỏe", "thuốc", "health"]):
            return Decimal("300000.00")
        else:
            return Decimal("250000.00")

    prompt_items = []
    default_recs: list[BudgetRecommendationItem] = []
    total_rec = Decimal("0.00")

    for cat in categories:
        prior_amounts = [cat_history_map.get((cat.id, y, m), Decimal("0.00")) for y, m in prior_slots]
        active_prior = [a for a in prior_amounts if a > Decimal("0.00")]
        
        # Average strictly across active prior months that have data
        if active_prior:
            avg_spent = (sum(active_prior) / Decimal(str(len(active_prior)))).quantize(Decimal("0.01"))
        else:
            avg_spent = Decimal("0.00")

        last_spent = last_month_spend_map.get(cat.id, Decimal("0.00"))
        curr_spent = current_month_spend_map.get(cat.id, Decimal("0.00"))
        cat_name_lower = (cat.name or "").lower()
        cat_expense_txns = [t for t in expense_txns if t[0] == cat.id]
        cat_txn_count = len(cat_expense_txns)

        if avg_spent > Decimal("0.00"):
            # Check if this category spend is only a tiny one-off test transaction without overall data sufficiency
            if not is_data_sufficient and avg_spent < Decimal("300000.00"):
                base_amount = _get_standard_baseline(cat_name_lower)
                reason = f"Đã ghi nhận chi tiêu sơ bộ {avg_spent:,.0f} đ ({cat_txn_count} giao dịch). Dữ liệu chưa đủ chu kỳ tháng, áp dụng định mức cơ bản tiêu chuẩn tham khảo."
            else:
                base_amount = avg_spent * Decimal("1.05")
                if len(active_prior) == lookback_months:
                    reason = f"Dựa trên mức chi trung bình {avg_spent:,.0f} đ ({lookback_months} tháng trước) kèm dự phòng 5%."
                else:
                    reason = f"Dựa trên mức chi trung bình {avg_spent:,.0f} đ ({len(active_prior)} tháng có dữ liệu) kèm dự phòng 5%."
        elif last_spent > Decimal("0.00"):
            if not is_data_sufficient and last_spent < Decimal("300000.00"):
                base_amount = _get_standard_baseline(cat_name_lower)
                reason = f"Đã ghi nhận chi tiêu sơ bộ {last_spent:,.0f} đ tháng trước. Dữ liệu chưa đủ chu kỳ tháng, áp dụng định mức cơ bản tiêu chuẩn tham khảo."
            else:
                base_amount = last_spent * Decimal("1.05")
                reason = f"Dựa trên mức chi {last_spent:,.0f} đ của tháng gần nhất."
        elif curr_spent > Decimal("0.00"):
            if is_target_current_month and days_passed < days_in_target_month:
                if curr_spent >= Decimal("200000.00") or cat_txn_count >= 2:
                    projected = (curr_spent / Decimal(str(days_passed))) * Decimal(str(days_in_target_month))
                    base_amount = projected * Decimal("1.05")
                    reason = f"Dựa trên mức chi {curr_spent:,.0f} đ ({days_passed} ngày đầu tháng, dự phóng ~{projected:,.0f} đ) kèm dự phòng 5%."
                else:
                    base_amount = _get_standard_baseline(cat_name_lower)
                    reason = f"Đã chi {curr_spent:,.0f} đ sơ bộ trong tháng. Áp dụng định mức tiêu chuẩn tham khảo cho đến khi đủ dữ liệu chu kỳ tháng."
            else:
                base_amount = curr_spent * Decimal("1.2")
                reason = f"Dựa trên mức chi {curr_spent:,.0f} đ đã phát sinh trong tháng."
        else:
            if is_income_sufficient:
                if any(k in cat_name_lower for k in ["ăn", "food", "uống", "dining"]):
                    base_amount = avg_monthly_income * Decimal("0.22")
                    reason = f"Định mức ăn uống (~22% thu nhập {avg_monthly_income:,.0f} đ theo chuẩn 50/30/20)."
                elif any(k in cat_name_lower for k in ["nhà", "phòng", "home", "rent", "trọ"]):
                    base_amount = avg_monthly_income * Decimal("0.20")
                    reason = f"Định mức nhà ở/tiền phòng (~20% thu nhập {avg_monthly_income:,.0f} đ theo chuẩn 50/30/20)."
                elif any(k in cat_name_lower for k in ["đi lại", "di chuyển", "xăng", "xe", "transport"]):
                    base_amount = avg_monthly_income * Decimal("0.05")
                    reason = "Định mức đi lại và xăng xe (~5% thu nhập theo quy tắc 50/30/20)."
                elif any(k in cat_name_lower for k in ["mua sắm", "shopping"]):
                    base_amount = avg_monthly_income * Decimal("0.08")
                    reason = "Hạn mức mua sắm đồ dùng (~8% thu nhập theo quy tắc 50/30/20)."
                elif any(k in cat_name_lower for k in ["giải trí", "entertainment", "chơi"]):
                    base_amount = avg_monthly_income * Decimal("0.06")
                    reason = "Quỹ giải trí, giao lưu (~6% thu nhập theo quy tắc 50/30/20)."
                elif any(k in cat_name_lower for k in ["giáo dục", "học", "sách", "education"]):
                    base_amount = avg_monthly_income * Decimal("0.05")
                    reason = "Chi phí học tập, phát triển bản thân (~5% thu nhập)."
                elif any(k in cat_name_lower for k in ["y tế", "sức khỏe", "thuốc", "health"]):
                    base_amount = avg_monthly_income * Decimal("0.04")
                    reason = "Quỹ dự phòng chăm sóc sức khỏe (~4% thu nhập)."
                else:
                    base_amount = avg_monthly_income * Decimal("0.03")
                    reason = "Dự trù chi phí nhỏ phát sinh (~3% thu nhập)."
            else:
                base_amount = _get_standard_baseline(cat_name_lower)
                reason = "Chưa đủ lịch sử chi tiêu và thu nhập chu kỳ tháng, áp dụng định mức cơ bản tiêu chuẩn tham khảo."

        # Ensure recommendation is not lower than already spent in target month
        if curr_spent > Decimal("0.00") and base_amount < curr_spent:
            base_amount = curr_spent * Decimal("1.1")
            reason = f"Đã chi {curr_spent:,.0f} đ trong tháng, đề xuất hạn mức an toàn kèm dự phòng."

        # Round to nearest 50,000 VND
        rec_rounded = int(math.ceil(float(base_amount) / 50000.0) * 50000)
        rec_amount = Decimal(str(max(50000, rec_rounded))).quantize(Decimal("0.01"))

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

    prompt = ""
    final_recs: list[BudgetRecommendationItem] = default_recs
    final_total: Decimal = total_rec

    # Prompt Gemini for AI-refined reasons and amounts
    from app.core.ai.gemini_client import get_gemini_model
    model_resolver = get_model_fn or get_gemini_model
    model = model_resolver(
        system_instruction=get_prompt("budget_recommendations", "system_instruction")
    )
    rag_context, applied_benchmarks = retrieve_contextual_budget_knowledge(
        prompt_items,
        target_month=target_month,
        target_year=target_year,
        monthly_income=avg_monthly_income if is_income_sufficient else Decimal("0"),
    )
    if model and prompt_items:
        data_status_str = (
            f"Dữ liệu đầy đủ ({total_expense_txn_count} giao dịch qua {date_span_days} ngày, {qualified_prior_months} tháng đạt chuẩn)"
            if is_data_sufficient
            else f"Dữ liệu sơ bộ ({total_expense_txn_count} giao dịch, khoảng cách {date_span_days} ngày - chưa đủ 1 chu kỳ tháng chuẩn)"
        )
        monthly_income_str = (
            f"{avg_monthly_income:,.0f} VNĐ"
            if is_income_sufficient
            else f"{avg_monthly_income:,.0f} VNĐ (khoản thu nhỏ lẻ / chưa đủ ngưỡng thu nhập chu kỳ chuẩn >= 2,000,000 VNĐ)"
            if avg_monthly_income > Decimal("0")
            else "Chưa có dữ liệu thu nhập"
        )
        prompt = format_prompt(
            "budget_recommendations",
            "user_prompt_template",
            target_month=target_month,
            target_year=target_year,
            data_status=data_status_str,
            monthly_income=monthly_income_str,
            items_json=json.dumps(prompt_items, ensure_ascii=False, indent=2),
        )
        if rag_context:
            prompt = f"{rag_context}\n\n{prompt}"
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
                    final_recs = updated_recs
                    final_total = new_total
        except Exception:
            pass

    try:
        from app.models.ai_report import AIReport
        from app.models.enums import ReportType
        from app.core.ai_chat import mask_sensitive_data
        log_entry = AIReport(
            user_id=user_id,
            report_type=ReportType.BUDGET_SUGGESTION,
            prompt_sent=mask_sensitive_data(prompt) if prompt else f"Budget Suggestion {target_month:02d}/{target_year}",
            ai_response=json.dumps([r.model_dump(mode="json") for r in final_recs], ensure_ascii=False),
            period_month=target_month,
            period_year=target_year,
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()

    if not applied_benchmarks:
        applied_benchmarks = [
        "VnExpress: Quy tắc quản lý tài chính 50/30/20 (https://vnexpress.net/quan-ly-tien-bang-quy-tac-50-30-20-4282825.html)",
        "VnExpress: Định mức tỷ trọng chi tiêu gia đình chuẩn (https://vnexpress.net/quy-tac-chi-tieu-gia-dinh-trong-thoi-kho-khan-vnepre-4864535.html)",
        "Trường ĐH Mở TP.HCM: Tài liệu Hoạch định Ngân sách Tài chính Cá nhân (https://sdh.ou.edu.vn/asset/ckfinder/userfiles/5/files/FIN617_Tai%20chinh%20ca%20nhan_Personal%20finance.pdf)",
    ]

    return BudgetRecommendationResponse(
        target_month=target_month,
        target_year=target_year,
        total_recommended=final_total,
        recommendations=final_recs,
        rag_benchmarks=applied_benchmarks,
    )


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
