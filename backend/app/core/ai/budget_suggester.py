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
    last_slot = prior_slots[-1]
    last_month_spend_map: dict[int, Decimal] = {c.id: Decimal("0.00") for c in categories}
    current_month_spend_map: dict[int, Decimal] = {c.id: Decimal("0.00") for c in categories}

    for cat_id, txn_date, amount in hist_txns:
        if not cat_id or not txn_date:
            continue
        amt = Decimal(str(amount or 0)).quantize(Decimal("0.01"))
        key = (cat_id, txn_date.year, txn_date.month)
        cat_history_map[key] = cat_history_map.get(key, Decimal("0.00")) + amt
        if (txn_date.year, txn_date.month) == last_slot:
            last_month_spend_map[cat_id] = last_month_spend_map.get(cat_id, Decimal("0.00")) + amt
        if txn_date.year == target_year and txn_date.month == target_month:
            current_month_spend_map[cat_id] = current_month_spend_map.get(cat_id, Decimal("0.00")) + amt

    prompt_items = []
    default_recs: list[BudgetRecommendationItem] = []
    total_rec = Decimal("0.00")

    for cat in categories:
        prior_amounts = [cat_history_map.get((cat.id, y, m), Decimal("0.00")) for y, m in prior_slots]
        active_prior = [a for a in prior_amounts if a > Decimal("0.00")]
        
        # Average strictly across prior months
        if active_prior:
            avg_spent = (sum(prior_amounts) / Decimal(str(lookback_months))).quantize(Decimal("0.01"))
        else:
            avg_spent = Decimal("0.00")

        last_spent = last_month_spend_map.get(cat.id, Decimal("0.00"))
        curr_spent = current_month_spend_map.get(cat.id, Decimal("0.00"))

        if avg_spent > Decimal("0.00"):
            base_amount = avg_spent * Decimal("1.05")
            reason = f"Dựa trên mức chi trung bình {avg_spent:,.0f} đ ({lookback_months} tháng trước) kèm dự phòng 5%."
        elif last_spent > Decimal("0.00"):
            base_amount = last_spent * Decimal("1.05")
            reason = f"Dựa trên mức chi {last_spent:,.0f} đ của tháng gần nhất."
        elif curr_spent > Decimal("0.00"):
            base_amount = curr_spent * Decimal("1.2")
            reason = f"Dựa trên mức chi {curr_spent:,.0f} đ đã phát sinh trong tháng."
        else:
            cat_name_lower = (cat.name or "").lower()
            if any(k in cat_name_lower for k in ["ăn", "food", "uống", "dining"]):
                base_amount = Decimal("2200000.00")
                reason = "Mức ăn uống cơ bản tiết kiệm cho người trẻ/người lao động."
            elif any(k in cat_name_lower for k in ["nhà", "phòng", "home", "rent", "trọ"]):
                base_amount = Decimal("1800000.00")
                reason = "Chi phí thuê phòng/nhà trọ cơ bản."
            elif any(k in cat_name_lower for k in ["đi lại", "di chuyển", "xăng", "xe", "transport"]):
                base_amount = Decimal("400000.00")
                reason = "Dự trù xăng xe và chi phí đi lại hằng tháng."
            elif any(k in cat_name_lower for k in ["mua sắm", "shopping"]):
                base_amount = Decimal("400000.00")
                reason = "Ngân sách mua sắm đồ dùng cá nhân thiết yếu."
            elif any(k in cat_name_lower for k in ["giải trí", "entertainment", "chơi"]):
                base_amount = Decimal("300000.00")
                reason = "Quỹ giao lưu bạn bè và thư giãn cuối tuần."
            elif any(k in cat_name_lower for k in ["giáo dục", "học", "sách", "education"]):
                base_amount = Decimal("300000.00")
                reason = "Chi phí học tập, tài liệu hoặc phát triển kỹ năng."
            elif any(k in cat_name_lower for k in ["y tế", "sức khỏe", "thuốc", "health"]):
                base_amount = Decimal("250000.00")
                reason = "Dự phòng y tế và thuốc men cơ bản."
            else:
                base_amount = Decimal("200000.00")
                reason = "Quỹ dự phòng cho các khoản chi tiêu nhỏ phát sinh."

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

    # Prompt Gemini for AI-refined reasons and amounts
    from app.core.ai.gemini_client import get_gemini_model
    model_resolver = get_model_fn or get_gemini_model
    model = model_resolver(
        system_instruction=get_prompt("budget_recommendations", "system_instruction")
    )
    if model and prompt_items:
        prompt = format_prompt(
            "budget_recommendations",
            "user_prompt_template",
            target_month=target_month,
            target_year=target_year,
            items_json=json.dumps(prompt_items, ensure_ascii=False, indent=2),
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
                    final_recs = updated_recs
                    final_total = new_total
        except Exception:
            pass

    if 'final_recs' not in locals():
        final_recs = default_recs
        final_total = total_rec

    try:
        from app.models.ai_report import AIReport
        from app.models.enums import ReportType
        from app.core.ai_chat import mask_sensitive_data
        log_entry = AIReport(
            user_id=user_id,
            report_type=ReportType.BUDGET_SUGGESTION,
            prompt_sent=mask_sensitive_data(prompt) if 'prompt' in locals() and prompt else f"Budget Suggestion {target_month:02d}/{target_year}",
            ai_response=json.dumps([r.model_dump(mode="json") for r in final_recs], ensure_ascii=False),
            period_month=target_month,
            period_year=target_year,
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()

    return BudgetRecommendationResponse(
        target_month=target_month,
        target_year=target_year,
        total_recommended=final_total,
        recommendations=final_recs,
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
