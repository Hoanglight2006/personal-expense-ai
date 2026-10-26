"""Budget service implementing monthly category budget management, spending calculation, and alerts."""

from __future__ import annotations

import calendar
from datetime import date
from app.core.timezone import local_today
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session, joinedload

from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.budget import (
    BudgetAlertItem,
    BudgetAlertResponse,
    BudgetCreate,
    BudgetListResponse,
    BudgetResponse,
    BudgetUpdate,
    CategorySimpleInfo,
)

BUDGET_NOT_FOUND = "Không tìm thấy ngân sách."


class BudgetService:
    """Service layer encapsulating budget business logic."""

    def __init__(self, db: Session, current_user: User) -> None:
        self.db = db
        self.user = current_user

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _owned_budget_or_404(self, budget_id: int) -> Budget:
        """Return a Budget owned by user or raise 404."""
        budget = (
            self.db.query(Budget)
            .options(joinedload(Budget.category))
            .filter(Budget.id == budget_id, Budget.user_id == self.user.id)
            .first()
        )
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=BUDGET_NOT_FOUND,
            )
        return budget

    @staticmethod
    def _calculate_budget_status(
        amount: Decimal, spent: Decimal
    ) -> tuple[Decimal, float, str]:
        remaining = amount - spent
        pct = round(float((spent / amount) * 100), 1) if amount > 0 else 0.0

        if spent >= amount:
            budget_status = "exceeded"
        elif spent >= amount * Decimal("0.8"):
            budget_status = "warning"
        else:
            budget_status = "normal"

        return remaining, pct, budget_status

    def _build_budget_response(self, budget: Budget, spent: Decimal) -> BudgetResponse:
        remaining, pct, b_status = self._calculate_budget_status(budget.amount, spent)
        cat_info = None
        if budget.category:
            cat_info = CategorySimpleInfo(
                id=budget.category.id,
                name=budget.category.name,
                icon=budget.category.icon,
                color=budget.category.color,
                type=budget.category.type,
                is_active=budget.category.is_active,
            )
        return BudgetResponse(
            id=budget.id,
            user_id=budget.user_id,
            category_id=budget.category_id,
            category=cat_info,
            amount=budget.amount,
            month=budget.month,
            year=budget.year,
            spent_amount=spent,
            remaining_amount=remaining,
            percentage_used=pct,
            status=b_status,
            created_at=budget.created_at,
        )

    # -----------------------------------------------------------------------
    # Public Business Methods
    # -----------------------------------------------------------------------

    def create_budget(self, payload: BudgetCreate) -> BudgetResponse:
        category = (
            self.db.query(Category)
            .filter(
                Category.id == payload.category_id,
                Category.user_id == self.user.id,
                Category.deleted_at.is_(None),
            )
            .with_for_update()
            .first()
        )
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy danh mục được chọn.",
            )

        if not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể thiết lập ngân sách cho danh mục đã ẩn.",
            )

        if category.type != CategoryType.EXPENSE.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ngân sách chỉ áp dụng cho danh mục Chi tiêu (Expense).",
            )

        existing = (
            self.db.query(Budget)
            .filter(
                Budget.user_id == self.user.id,
                Budget.category_id == payload.category_id,
                Budget.month == payload.month,
                Budget.year == payload.year,
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Đã thiết lập ngân sách cho danh mục “{category.name}” trong tháng {payload.month}/{payload.year}.",
            )

        new_budget = Budget(
            user_id=self.user.id,
            category_id=payload.category_id,
            amount=payload.amount,
            month=payload.month,
            year=payload.year,
        )
        self.db.add(new_budget)
        self.db.commit()
        self.db.refresh(new_budget)

        last_day = calendar.monthrange(payload.year, payload.month)[1]
        start_date = date(payload.year, payload.month, 1)
        end_date = date(payload.year, payload.month, last_day)

        spent_sum = (
            self.db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), Decimal("0")))
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.category_id == payload.category_id,
                Transaction.type == CategoryType.EXPENSE,
                Transaction.is_deleted.is_(False),
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .scalar()
            or Decimal("0.00")
        )

        new_budget.category = category
        res = self._build_budget_response(new_budget, spent_sum)
        try:
            from app.services.financial_alert_service import FinancialAlertService
            FinancialAlertService(self.db, self.user).check_and_send_budget_alerts(
                category_id=new_budget.category_id,
                month=new_budget.month,
                year=new_budget.year,
            )
        except Exception:
            pass
        return res

    def get_budgets(
        self, *, month: int | None = None, year: int | None = None
    ) -> BudgetListResponse:
        today = local_today()
        target_month = month or today.month
        target_year = year or today.year

        last_day = calendar.monthrange(target_year, target_month)[1]
        start_date = date(target_year, target_month, 1)
        end_date = date(target_year, target_month, last_day)

        budgets = (
            self.db.query(Budget)
            .options(joinedload(Budget.category))
            .filter(
                Budget.user_id == self.user.id,
                Budget.month == target_month,
                Budget.year == target_year,
            )
            .order_by(Budget.created_at.asc())
            .all()
        )

        if not budgets:
            return BudgetListResponse(
                month=target_month,
                year=target_year,
                total_budget=Decimal("0.00"),
                total_spent=Decimal("0.00"),
                total_remaining=Decimal("0.00"),
                items=[],
            )

        spent_rows = (
            self.db.query(
                Transaction.category_id,
                sa_func.coalesce(sa_func.sum(Transaction.amount), Decimal("0")).label(
                    "total_spent"
                ),
            )
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.type == CategoryType.EXPENSE,
                Transaction.is_deleted.is_(False),
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .group_by(Transaction.category_id)
            .all()
        )
        spent_map = {row[0]: Decimal(str(row[1])) for row in spent_rows}

        items = []
        total_budget = Decimal("0.00")
        total_spent = Decimal("0.00")

        for b in budgets:
            spent = spent_map.get(b.category_id, Decimal("0.00"))
            items.append(self._build_budget_response(b, spent))
            total_budget += b.amount
            total_spent += spent

        total_remaining = total_budget - total_spent

        return BudgetListResponse(
            month=target_month,
            year=target_year,
            total_budget=total_budget,
            total_spent=total_spent,
            total_remaining=total_remaining,
            items=items,
        )

    def get_budget_alerts(
        self, *, month: int | None = None, year: int | None = None
    ) -> BudgetAlertResponse:
        budget_list = self.get_budgets(month=month, year=year)

        alert_items = []
        for item in budget_list.items:
            if item.status in ("warning", "exceeded"):
                alert_items.append(
                    BudgetAlertItem(
                        id=item.id,
                        category_id=item.category_id,
                        category_name=item.category.name if item.category else "Danh mục",
                        category_icon=item.category.icon if item.category else "other",
                        category_color=item.category.color if item.category else "#D69A23",
                        amount=item.amount,
                        spent_amount=item.spent_amount,
                        percentage_used=item.percentage_used,
                        status=item.status,
                    )
                )

        alert_items.sort(key=lambda a: a.percentage_used, reverse=True)
        return BudgetAlertResponse(count=len(alert_items), items=alert_items)

    def get_budget(self, budget_id: int) -> BudgetResponse:
        budget = self._owned_budget_or_404(budget_id)

        last_day = calendar.monthrange(budget.year, budget.month)[1]
        start_date = date(budget.year, budget.month, 1)
        end_date = date(budget.year, budget.month, last_day)

        spent_sum = (
            self.db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), Decimal("0")))
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.category_id == budget.category_id,
                Transaction.type == CategoryType.EXPENSE,
                Transaction.is_deleted.is_(False),
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .scalar()
            or Decimal("0.00")
        )

        return self._build_budget_response(budget, spent_sum)

    def update_budget(self, budget_id: int, payload: BudgetUpdate) -> BudgetResponse:
        budget = self._owned_budget_or_404(budget_id)
        budget.amount = payload.amount
        self.db.commit()
        self.db.refresh(budget)

        last_day = calendar.monthrange(budget.year, budget.month)[1]
        start_date = date(budget.year, budget.month, 1)
        end_date = date(budget.year, budget.month, last_day)

        spent_sum = (
            self.db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), Decimal("0")))
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.category_id == budget.category_id,
                Transaction.type == CategoryType.EXPENSE,
                Transaction.is_deleted.is_(False),
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
            )
            .scalar()
            or Decimal("0.00")
        )

        res = self._build_budget_response(budget, spent_sum)
        try:
            from app.services.financial_alert_service import FinancialAlertService
            FinancialAlertService(self.db, self.user).check_and_send_budget_alerts(
                category_id=budget.category_id,
                month=budget.month,
                year=budget.year,
            )
        except Exception:
            pass
        return res

    def delete_budget(self, budget_id: int) -> dict[str, str]:
        budget = self._owned_budget_or_404(budget_id)
        self.db.delete(budget)
        self.db.commit()
        return {"detail": "Đã xóa ngân sách thành công."}
