"""Category service implementing core business logic for income and expense categories."""

from __future__ import annotations

import time
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.core.category_defaults import add_missing_default_categories
from app.core.timezone import local_today
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategorySort,
    CategoryStatusFilter,
    CategoryUpdate,
    category_name_key,
)

CATEGORY_NOT_FOUND = "Không tìm thấy danh mục."
CATEGORY_NAME_CONFLICT = "Tên danh mục đã tồn tại."


class CategoryService:
    """Service layer encapsulating category business logic."""

    def __init__(self, db: Session, current_user: User) -> None:
        self.db = db
        self.user = current_user

    @staticmethod
    def default_period() -> tuple[date, date]:
        today = local_today()
        return today.replace(day=1), today.replace(day=monthrange(today.year, today.month)[1])

    @classmethod
    def validated_period(cls, start_date: date | None, end_date: date | None) -> tuple[date, date]:
        default_start, default_end = cls.default_period()
        period_start = start_date or default_start
        period_end = end_date or default_end
        if period_start > period_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ngày bắt đầu không được sau ngày kết thúc.",
            )
        return period_start, period_end

    def _owned_category_or_404(
        self,
        category_id: int,
        *,
        include_deleted: bool = False,
        lock: bool = False,
    ) -> Category:
        query = self.db.query(Category).filter(
            Category.id == category_id, Category.user_id == self.user.id
        )
        if not include_deleted:
            query = query.filter(Category.deleted_at.is_(None))
        if lock:
            query = query.with_for_update()
        category = query.first()
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CATEGORY_NOT_FOUND)
        return category

    def _ensure_unique_name(
        self,
        name_normalized: str,
        exclude_id: int | None = None,
    ) -> None:
        query = self.db.query(Category.id).filter(
            Category.user_id == self.user.id,
            Category.name_normalized == name_normalized,
        )
        if exclude_id is not None:
            query = query.filter(Category.id != exclude_id)
        if query.first() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CATEGORY_NAME_CONFLICT)

    def _commit_category(self, category: Category) -> Category:
        try:
            self.db.commit()
        except DataError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Dữ liệu danh mục vượt quá giới hạn lưu trữ.",
            )
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CATEGORY_NAME_CONFLICT)
        self.db.refresh(category)
        return category

    def _category_response(self, category: Category) -> CategoryResponse:
        has_transactions = (
            self.db.query(Transaction.id)
            .filter(
                Transaction.user_id == category.user_id,
                Transaction.category_id == category.id,
                Transaction.is_deleted.is_(False),
            )
            .first()
            is not None
        )
        return CategoryResponse.model_validate(category).model_copy(
            update={"has_transactions": has_transactions}
        )

    def _category_rows_with_stats(
        self,
        period_start: date,
        period_end: date,
        search: str | None = None,
        category_status: CategoryStatusFilter = "active",
        sort: CategorySort = "amount_desc",
        category_id: int | None = None,
        include_deleted_with_transactions: bool = False,
    ) -> list[CategoryResponse]:
        stats = (
            self.db.query(
                Transaction.category_id.label("category_id"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total_amount"),
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.type == CategoryType.EXPENSE, Transaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("expense_amount"),
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.type == CategoryType.INCOME, Transaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("income_amount"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.is_deleted.is_(False),
                Transaction.transaction_date >= period_start,
                Transaction.transaction_date <= period_end,
            )
            .group_by(Transaction.category_id)
            .subquery()
        )
        amount_expression = func.coalesce(stats.c.total_amount, 0)
        query = (
            self.db.query(
                Category,
                amount_expression,
                func.coalesce(stats.c.expense_amount, 0),
                func.coalesce(stats.c.income_amount, 0),
                func.coalesce(stats.c.transaction_count, 0),
            )
            .outerjoin(stats, stats.c.category_id == Category.id)
            .filter(Category.user_id == self.user.id)
        )
        if category_id is not None:
            query = query.filter(Category.id == category_id)
        if search:
            normalized_search = search.strip().casefold()
            if normalized_search:
                query = query.filter(
                    Category.name_normalized.contains(normalized_search, autoescape=True)
                )

        # Always filter out soft-deleted categories
        if include_deleted_with_transactions:
            query = query.filter(
                (Category.deleted_at.is_(None))
                | (func.coalesce(stats.c.transaction_count, 0) > 0)
            )
        else:
            # Always filter out soft-deleted categories
            query = query.filter(Category.deleted_at.is_(None))

        if category_status == "active":
            query = query.filter(Category.is_active.is_(True))
        elif category_status == "hidden":
            query = query.filter(Category.is_active.is_(False))

        if sort == "amount_asc":
            query = query.order_by(amount_expression.asc(), Category.name.asc())
        elif sort == "name_asc":
            query = query.order_by(Category.name.asc())
        else:
            query = query.order_by(amount_expression.desc(), Category.name.asc())

        total_expense = Decimal(
            self.db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.is_deleted.is_(False),
                Transaction.type == CategoryType.EXPENSE,
                Transaction.transaction_date >= period_start,
                Transaction.transaction_date <= period_end,
            )
            .scalar()
            or 0
        )
        used_category_ids = {
            row[0]
            for row in self.db.query(Transaction.category_id)
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.is_deleted.is_(False),
            )
            .distinct()
            .all()
        }
        responses: list[CategoryResponse] = []
        for category, total_amount, expense_amount, income_amount, transaction_count in query.all():
            amount = Decimal(total_amount or 0).quantize(Decimal("0.01"))
            category_expense = Decimal(expense_amount or 0).quantize(Decimal("0.01"))
            category_income = Decimal(income_amount or 0).quantize(Decimal("0.01"))
            percentage = Decimal("0.00")
            if total_expense > 0:
                percentage = (
                    category_expense / total_expense * Decimal("100")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            response = CategoryResponse.model_validate(category).model_copy(
                update={
                    "is_deleted": category.deleted_at is not None,
                    "deleted_at": category.deleted_at,
                    "total_amount": amount,
                    "income_amount": category_income,
                    "expense_amount": category_expense,
                    "transaction_count": int(transaction_count or 0),
                    "expense_percentage": percentage,
                    "has_transactions": category.id in used_category_ids,
                }
            )
            responses.append(response)
        return responses

    # -----------------------------------------------------------------------
    # Public Methods
    # -----------------------------------------------------------------------

    def create_category(self, category_in: CategoryCreate) -> CategoryResponse:
        normalized_name = category_name_key(category_in.name)
        self._ensure_unique_name(normalized_name)
        category = Category(
            user_id=self.user.id,
            name=category_in.name,
            name_normalized=normalized_name,
            type=category_in.type,
            icon=category_in.icon,
            color=category_in.color,
        )
        self.db.add(category)
        self._commit_category(category)
        return self._category_response(category)

    def create_defaults(self) -> list[CategoryResponse]:
        created = add_missing_default_categories(self.db, self.user.id)
        try:
            self.db.commit()
        except DataError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Dữ liệu danh mục vượt quá giới hạn lưu trữ.",
            )
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CATEGORY_NAME_CONFLICT)
        for category in created:
            self.db.refresh(category)
        return [self._category_response(category) for category in created]

    def list_categories(
        self,
        *,
        search: str | None = None,
        status_filter: CategoryStatusFilter = "active",
        sort: CategorySort = "amount_desc",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CategoryListResponse:
        period_start, period_end = self.validated_period(start_date, end_date)
        items = self._category_rows_with_stats(
            period_start,
            period_end,
            search=search,
            category_status=status_filter,
            sort=sort,
        )
        return CategoryListResponse(start_date=period_start, end_date=period_end, items=items)

    def get_statistics(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CategoryListResponse:
        period_start, period_end = self.validated_period(start_date, end_date)
        items = self._category_rows_with_stats(
            period_start,
            period_end,
            category_status="all",
            sort="amount_desc",
            include_deleted_with_transactions=True,
        )
        return CategoryListResponse(start_date=period_start, end_date=period_end, items=items)

    def get_category(
        self,
        category_id: int,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CategoryResponse:
        self._owned_category_or_404(category_id)
        period_start, period_end = self.validated_period(start_date, end_date)
        return self._category_rows_with_stats(
            period_start,
            period_end,
            category_status="all",
            category_id=category_id,
        )[0]

    def update_category(
        self,
        category_id: int,
        category_in: CategoryUpdate,
    ) -> CategoryResponse:
        category = self._owned_category_or_404(category_id, lock=True)
        changes = category_in.model_dump(exclude_unset=True)
        if "type" in changes and changes["type"] != category.type:
            has_transactions = (
                self.db.query(Transaction.id)
                .filter(
                    Transaction.category_id == category.id,
                    Transaction.user_id == self.user.id,
                )
                .first()
                is not None
            )
            has_budgets = (
                self.db.query(Budget.id)
                .filter(
                    Budget.category_id == category.id,
                    Budget.user_id == self.user.id,
                )
                .first()
                is not None
            )
            if has_transactions or has_budgets:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Không thể đổi loại danh mục đã được sử dụng cho giao dịch "
                        "hoặc ngân sách."
                    ),
                )
        next_name = changes.get("name", category.name)
        normalized_name = category_name_key(next_name)
        self._ensure_unique_name(normalized_name, exclude_id=category.id)
        for field, value in changes.items():
            setattr(category, field, value)
        category.name_normalized = normalized_name
        self._commit_category(category)
        return self._category_response(category)

    def hide_category(self, category_id: int) -> CategoryResponse:
        category = self._owned_category_or_404(category_id)
        category.is_active = False
        self._commit_category(category)
        return self._category_response(category)

    def restore_category(self, category_id: int) -> CategoryResponse:
        category = self._owned_category_or_404(category_id)
        normalized_name = category_name_key(category.name)
        self._ensure_unique_name(normalized_name, exclude_id=category.id)
        category.name_normalized = normalized_name
        category.is_active = True
        self._commit_category(category)
        return self._category_response(category)

    def delete_category(self, category_id: int) -> None:
        category = self._owned_category_or_404(category_id)
        if category.deleted_at is not None:
            return

        timestamp = str(int(time.time()))
        category.name_normalized = f"{category.name_normalized[:120]}_del_{timestamp}"
        category.deleted_at = func.now()
        category.is_active = False
        self._commit_category(category)
