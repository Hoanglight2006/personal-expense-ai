"""Transaction service implementing core business logic for transactions.

Encapsulates all database operations, balance safety validations, soft-delete,
restore, duplication, and bulk import flows.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func as sa_func, or_
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import CategoryType, ContributionSource, GoalStatus, PaymentMethod
from app.core.timezone import local_today
from app.models.saving_contribution import SavingContribution
from app.models.saving_goal import SavingGoal
from app.models.saving_withdrawal import SavingWithdrawal
from app.models.saving_withdrawal_allocation import SavingWithdrawalAllocation
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    CategoryInfo,
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionRestoreResponse,
    TransactionSort,
    TransactionSummaryResponse,
    TransactionUpdate,
)

TRANSACTION_NOT_FOUND = "Không tìm thấy giao dịch."
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def recomputed_goal_current_amount(
    db: Session,
    goal_id: int,
    *,
    exclude_transaction_id: int | None = None,
    restore_transaction_id: int | None = None,
) -> Decimal:
    """Rebuild savings from effective deposits minus their consumed amounts."""
    manual_contributions = (
        db.query(SavingContribution)
        .filter(
            SavingContribution.saving_goal_id == goal_id,
            SavingContribution.source == ContributionSource.MANUAL,
        )
        .all()
    )

    allocation_query = (
        db.query(SavingContribution)
        .join(Transaction, Transaction.id == SavingContribution.transaction_id)
        .filter(
            SavingContribution.saving_goal_id == goal_id,
            SavingContribution.source == ContributionSource.INCOME_ALLOCATION,
        )
    )
    if restore_transaction_id is not None:
        allocation_query = allocation_query.filter(
            or_(
                Transaction.is_deleted.is_(False),
                Transaction.id == restore_transaction_id,
            )
        )
    else:
        allocation_query = allocation_query.filter(Transaction.is_deleted.is_(False))
    if exclude_transaction_id is not None:
        allocation_query = allocation_query.filter(
            Transaction.id != exclude_transaction_id
        )

    effective_contributions = manual_contributions + allocation_query.all()
    contribution_ids = [contribution.id for contribution in effective_contributions]
    allocated_by_contribution = {
        contribution_id: Decimal(str(allocated_amount))
        for contribution_id, allocated_amount in (
            db.query(
                SavingWithdrawalAllocation.contribution_id,
                sa_func.coalesce(sa_func.sum(SavingWithdrawalAllocation.amount), 0),
            )
            .filter(SavingWithdrawalAllocation.contribution_id.in_(contribution_ids))
            .group_by(SavingWithdrawalAllocation.contribution_id)
            .all()
            if contribution_ids
            else []
        )
    }
    return sum(
        (
            max(
                Decimal("0.00"),
                Decimal(str(contribution.amount))
                - allocated_by_contribution.get(contribution.id, Decimal("0.00")),
            )
            for contribution in effective_contributions
        ),
        Decimal("0.00"),
    )


_recomputed_goal_current_amount = recomputed_goal_current_amount


class TransactionService:
    """Service layer encapsulating transaction business logic."""

    def __init__(self, db: Session, current_user: User) -> None:
        self.db = db
        self.user = current_user

    def _recomputed_goal_current_amount(
        self,
        goal_id: int,
        *,
        exclude_transaction_id: int | None = None,
        restore_transaction_id: int | None = None,
    ) -> Decimal:
        return recomputed_goal_current_amount(
            self.db,
            goal_id,
            exclude_transaction_id=exclude_transaction_id,
            restore_transaction_id=restore_transaction_id,
        )

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _lock_user_balance(self) -> None:
        """Serialize balance-changing operations for the user until commit/rollback."""
        self.db.query(User.id).filter(User.id == self.user.id).with_for_update().one()

    def _balance_effect(self, transaction_type: CategoryType, amount: Decimal) -> Decimal:
        normalized_amount = Decimal(str(amount))
        return (
            normalized_amount
            if transaction_type == CategoryType.INCOME
            else -normalized_amount
        )

    def _get_user_available_balance(self) -> Decimal:
        """Compute available unallocated balance = Total Income - Total Expense - Total in Active/Completed Saving Goals."""
        income_sum = (
            self.db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.type == CategoryType.INCOME,
                Transaction.is_deleted.is_(False),
            )
            .scalar()
        )
        expense_sum = (
            self.db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.type == CategoryType.EXPENSE,
                Transaction.is_deleted.is_(False),
            )
            .scalar()
        )
        saving_sum = (
            self.db.query(sa_func.coalesce(sa_func.sum(SavingGoal.current_amount), 0))
            .filter(
                SavingGoal.user_id == self.user.id,
                SavingGoal.status != GoalStatus.CANCELLED,
            )
            .scalar()
        )
        return (
            Decimal(str(income_sum))
            - Decimal(str(expense_sum))
            - Decimal(str(saving_sum))
        )

    def _ensure_projected_balance(self, delta: Decimal, detail: str) -> None:
        if self._get_user_available_balance() + delta < Decimal("0"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    def _commit_or_raise(self) -> None:
        try:
            self.db.commit()
        except DataError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Dữ liệu giao dịch vượt quá giới hạn lưu trữ.",
            )
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dữ liệu giao dịch xung đột. Vui lòng thử lại.",
            )

    def _owned_transaction_or_404(
        self,
        transaction_id: int,
        *,
        include_deleted: bool = False,
    ) -> Transaction:
        """Return a Transaction owned by user or raise 404."""
        if transaction_id >= 1_000_000_000:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=TRANSACTION_NOT_FOUND
            )
        query = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == self.user.id,
        )
        if not include_deleted:
            query = query.filter(Transaction.is_deleted.is_(False))
        txn = query.first()
        if txn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=TRANSACTION_NOT_FOUND
            )
        return txn

    def _validate_category(
        self,
        category_id: int,
        transaction_type: CategoryType,
        *,
        require_active: bool = True,
    ) -> Category:
        """Ensure the category belongs to the user and is not deleted."""
        category = (
            self.db.query(Category)
            .filter(
                Category.id == category_id,
                Category.user_id == self.user.id,

            )
            .with_for_update()
            .first()
        )
        if category is None or (require_active and category.deleted_at is not None):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy danh mục.",
            )
        if require_active and not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Không thể sử dụng danh mục đã ẩn cho giao dịch mới.",
            )
        if category.type != transaction_type.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Loại giao dịch không khớp với loại danh mục.",
            )
        return category

    def _to_response(self, txn: Transaction) -> TransactionResponse:
        category_info = None
        if txn.category:
            category_info = CategoryInfo(
                id=txn.category.id,
                name=txn.category.name,
                icon=txn.category.icon,
                color=txn.category.color,
                is_active=txn.category.is_active,
                is_deleted=txn.category.deleted_at is not None,
                deleted_at=txn.category.deleted_at,
            )
        saving_goal_id = None
        saving_goal_name = None
        saving_goal_amount = None
        if txn.type == CategoryType.INCOME:
            contrib = (
                self.db.query(SavingContribution, SavingGoal.name)
                .join(SavingGoal, SavingGoal.id == SavingContribution.saving_goal_id)
                .filter(SavingContribution.transaction_id == txn.id)
                .first()
            )
            if contrib:
                saving_goal_id = contrib[0].saving_goal_id
                saving_goal_name = contrib[1]
                saving_goal_amount = contrib[0].amount

        return TransactionResponse(
            id=txn.id,
            amount=txn.amount,
            type=txn.type,
            category_id=txn.category_id,
            category=category_info,
            transaction_date=txn.transaction_date,
            description=txn.description,
            payment_method=txn.payment_method,
            is_deleted=txn.is_deleted,
            created_at=txn.created_at,
            updated_at=txn.updated_at,
            deleted_at=txn.deleted_at,
            saving_goal_id=saving_goal_id,
            saving_goal_name=saving_goal_name,
            saving_goal_amount=saving_goal_amount,
            movement_type=None,
        )

    def _saving_contribution_to_response(self, c: SavingContribution, goal_name: str) -> TransactionResponse:
        saving_cat = CategoryInfo(
            id=0,
            name="Hũ tiết kiệm",
            icon="savings",
            color="#6366F1",
            is_active=True,
        )
        note_suffix = f" - {c.note}" if c.note else ""
        t_date = c.created_at.date() if isinstance(c.created_at, (datetime, date)) else local_today()
        c_at = c.created_at or datetime.now(timezone.utc)
        return TransactionResponse(
            id=1_000_000_000 + c.id,
            amount=c.amount,
            type=CategoryType.TRANSFER,
            category_id=0,
            category=saving_cat,
            transaction_date=t_date,
            description=f"Nạp vào hũ: {goal_name}{note_suffix}",
            payment_method=PaymentMethod.CASH,
            is_deleted=False,
            created_at=c_at,
            updated_at=c_at,
            deleted_at=None,
            saving_goal_id=c.saving_goal_id,
            saving_goal_name=goal_name,
            saving_goal_amount=c.amount,
            movement_type="deposit",
        )

    def _saving_withdrawal_to_response(self, w: SavingWithdrawal, goal_name: str) -> TransactionResponse:
        withdraw_cat = CategoryInfo(
            id=0,
            name="Rút tiết kiệm",
            icon="savings",
            color="#0EA5E9",
            is_active=True,
        )
        note_suffix = f" - {w.note}" if w.note else ""
        t_date = w.created_at.date() if isinstance(w.created_at, (datetime, date)) else local_today()
        w_at = w.created_at or datetime.now(timezone.utc)
        return TransactionResponse(
            id=2_000_000_000 + w.id,
            amount=w.amount,
            type=CategoryType.TRANSFER,
            category_id=0,
            category=withdraw_cat,
            transaction_date=t_date,
            description=f"Rút từ hũ: {goal_name}{note_suffix}",
            payment_method=PaymentMethod.CASH,
            is_deleted=False,
            created_at=w_at,
            updated_at=w_at,
            deleted_at=None,
            saving_goal_id=w.saving_goal_id,
            saving_goal_name=goal_name,
            saving_goal_amount=w.amount,
            movement_type="withdraw",
        )

    def _get_saving_responses(
        self,
        *,
        search: str | None = None,
        date_start: date | None = None,
        date_end: date | None = None,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        category_id: int | None = None,
        payment_method: PaymentMethod | None = None,
    ) -> list[TransactionResponse]:
        if category_id is not None and category_id != 0:
            return []
        if payment_method is not None and payment_method != PaymentMethod.CASH:
            return []

        c_query = (
            self.db.query(SavingContribution, SavingGoal.name)
            .join(SavingGoal, SavingGoal.id == SavingContribution.saving_goal_id)
            .filter(
                SavingGoal.user_id == self.user.id,
                SavingContribution.source == ContributionSource.MANUAL,
            )
        )
        w_query = (
            self.db.query(SavingWithdrawal, SavingGoal.name)
            .join(SavingGoal, SavingGoal.id == SavingWithdrawal.saving_goal_id)
            .filter(SavingGoal.user_id == self.user.id)
        )

        if amount_min is not None:
            c_query = c_query.filter(SavingContribution.amount >= amount_min)
            w_query = w_query.filter(SavingWithdrawal.amount >= amount_min)
        if amount_max is not None:
            c_query = c_query.filter(SavingContribution.amount <= amount_max)
            w_query = w_query.filter(SavingWithdrawal.amount <= amount_max)

        c_items = c_query.all()
        w_items = w_query.all()

        responses = [self._saving_contribution_to_response(c, name) for c, name in c_items]
        responses.extend([self._saving_withdrawal_to_response(w, name) for w, name in w_items])

        if date_start:
            responses = [r for r in responses if r.transaction_date >= date_start]
        if date_end:
            responses = [r for r in responses if r.transaction_date <= date_end]
        if search:
            kw = search.strip().lower()
            responses = [
                r for r in responses
                if kw in (r.description or "").lower() or kw in (r.saving_goal_name or "").lower()
            ]

        return responses

    def _recomputed_goal_current_amount(
        self,
        goal_id: int,
        *,
        exclude_transaction_id: int | None = None,
        restore_transaction_id: int | None = None,
    ) -> Decimal:
        """Rebuild savings from effective deposits minus their consumed amounts."""
        manual_contributions = (
            self.db.query(SavingContribution)
            .filter(
                SavingContribution.saving_goal_id == goal_id,
                SavingContribution.source == ContributionSource.MANUAL,
            )
            .all()
        )

        allocation_query = (
            self.db.query(SavingContribution)
            .join(Transaction, Transaction.id == SavingContribution.transaction_id)
            .filter(
                SavingContribution.saving_goal_id == goal_id,
                SavingContribution.source == ContributionSource.INCOME_ALLOCATION,
            )
        )
        if restore_transaction_id is not None:
            allocation_query = allocation_query.filter(
                or_(
                    Transaction.is_deleted.is_(False),
                    Transaction.id == restore_transaction_id,
                )
            )
        else:
            allocation_query = allocation_query.filter(Transaction.is_deleted.is_(False))
        if exclude_transaction_id is not None:
            allocation_query = allocation_query.filter(
                Transaction.id != exclude_transaction_id
            )

        effective_contributions = manual_contributions + allocation_query.all()
        contribution_ids = [contribution.id for contribution in effective_contributions]
        allocated_by_contribution = {
            contribution_id: Decimal(str(allocated_amount))
            for contribution_id, allocated_amount in (
                self.db.query(
                    SavingWithdrawalAllocation.contribution_id,
                    sa_func.coalesce(sa_func.sum(SavingWithdrawalAllocation.amount), 0),
                )
                .filter(SavingWithdrawalAllocation.contribution_id.in_(contribution_ids))
                .group_by(SavingWithdrawalAllocation.contribution_id)
                .all()
                if contribution_ids
                else []
            )
        }
        return sum(
            (
                max(
                    Decimal("0.00"),
                    Decimal(str(contribution.amount))
                    - allocated_by_contribution.get(contribution.id, Decimal("0.00")),
                )
                for contribution in effective_contributions
            ),
            Decimal("0.00"),
        )

    # -----------------------------------------------------------------------
    # Public Business Methods
    # -----------------------------------------------------------------------

    def create_transaction(self, payload: TransactionCreate) -> TransactionResponse:
        if payload.type == CategoryType.TRANSFER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Giao dịch loại tiết kiệm được tự động tạo khi nạp hoặc rút từ mục tiêu tiết kiệm.",
            )
        self._lock_user_balance()
        self._validate_category(payload.category_id, payload.type, require_active=True)

        allocation = (
            payload.saving_goal_amount
            if payload.saving_goal_id is not None and payload.saving_goal_amount is not None
            else Decimal("0")
        )
        delta = self._balance_effect(payload.type, payload.amount) - allocation
        self._ensure_projected_balance(
            delta,
            (
                f"Số tiền chi tiêu ({payload.amount:,.0f} đ) vượt quá số dư khả dụng "
                "hiện có. Vui lòng thêm thu nhập trước khi chi tiêu."
            ),
        )

        goal = None
        if payload.type == CategoryType.INCOME and payload.saving_goal_id is not None:
            goal = (
                self.db.query(SavingGoal)
                .filter(
                    SavingGoal.id == payload.saving_goal_id,
                    SavingGoal.user_id == self.user.id,
                )
                .with_for_update()
                .first()
            )
            if goal is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy mục tiêu tiết kiệm.",
                )
            if goal.status == GoalStatus.CANCELLED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mục tiêu tiết kiệm đã bị hủy hoặc tạm dừng.",
                )

        txn = Transaction(
            user_id=self.user.id,
            category_id=payload.category_id,
            type=payload.type,
            amount=payload.amount,
            description=payload.description,
            transaction_date=payload.transaction_date,
            payment_method=payload.payment_method,
        )
        self.db.add(txn)
        self.db.flush()

        if goal is not None and payload.saving_goal_amount is not None:
            contrib = SavingContribution(
                saving_goal_id=goal.id,
                transaction_id=txn.id,
                amount=payload.saving_goal_amount,
                source=ContributionSource.INCOME_ALLOCATION,
                note=f"Trích từ nguồn thu: {txn.description or 'Thu nhập'}",
            )
            self.db.add(contrib)
            goal.current_amount = Decimal(str(goal.current_amount)) + payload.saving_goal_amount
            if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
                goal.status = GoalStatus.COMPLETED

        self._commit_or_raise()
        self.db.refresh(txn)

        if txn.type == CategoryType.EXPENSE:
            try:
                from app.services.financial_alert_service import FinancialAlertService
                FinancialAlertService(self.db, self.user).check_and_send_budget_alerts(category_id=txn.category_id, month=txn.transaction_date.month if txn.transaction_date else None, year=txn.transaction_date.year if txn.transaction_date else None)
            except Exception:
                pass

        return self._to_response(txn)

    def list_transactions(
        self,
        *,
        search: str | None = None,
        date_start: date | None = None,
        date_end: date | None = None,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        type: CategoryType | None = None,
        category_id: int | None = None,
        payment_method: PaymentMethod | None = None,
        sort: TransactionSort = "date_desc",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> TransactionListResponse:
        if date_start and date_end and date_start > date_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ngày bắt đầu không được sau ngày kết thúc.",
            )
        if amount_min is not None and amount_max is not None and amount_min > amount_max:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Số tiền tối thiểu không được lớn hơn số tiền tối đa.",
            )
        if category_id is not None:
            cat = (
                self.db.query(Category)
                .filter(Category.id == category_id, Category.user_id == self.user.id)
                .first()
            )
            if cat is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy danh mục.",
                )

        query = self.db.query(Transaction).filter(
            Transaction.user_id == self.user.id,
            Transaction.is_deleted.is_(False),
        )

        if search:
            keyword = search.strip()
            if keyword:
                query = query.filter(
                    Transaction.description.contains(keyword, autoescape=True)
                )
        if date_start:
            query = query.filter(Transaction.transaction_date >= date_start)
        if date_end:
            query = query.filter(Transaction.transaction_date <= date_end)
        if amount_min is not None:
            query = query.filter(Transaction.amount >= amount_min)
        if amount_max is not None:
            query = query.filter(Transaction.amount <= amount_max)
        if type:
            query = query.filter(Transaction.type == type)
        if category_id is not None:
            query = query.filter(Transaction.category_id == category_id)
        if payment_method:
            query = query.filter(Transaction.payment_method == payment_method)

        def _sort_key(x: TransactionResponse):
            ts = x.created_at.timestamp() if x.created_at else 0.0
            return (x.transaction_date, ts, x.id)

        if type == CategoryType.TRANSFER:
            saving_items = self._get_saving_responses(
                search=search,
                date_start=date_start,
                date_end=date_end,
                amount_min=amount_min,
                amount_max=amount_max,
                category_id=category_id,
                payment_method=payment_method,
            )
            total_count = len(saving_items)
            if sort == "date_asc":
                saving_items.sort(key=_sort_key)
            elif sort == "amount_desc":
                saving_items.sort(key=lambda x: x.amount, reverse=True)
            elif sort == "amount_asc":
                saving_items.sort(key=lambda x: x.amount)
            else:
                saving_items.sort(key=_sort_key, reverse=True)

            offset = (page - 1) * page_size
            return TransactionListResponse(
                items=saving_items[offset : offset + page_size],
                total_count=total_count,
                page=page,
                page_size=page_size,
            )

        if type in (CategoryType.EXPENSE, CategoryType.INCOME):
            total_count = query.count()
            if sort == "date_asc":
                query = query.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
            elif sort == "amount_desc":
                query = query.order_by(Transaction.amount.desc(), Transaction.id.desc())
            elif sort == "amount_asc":
                query = query.order_by(Transaction.amount.asc(), Transaction.id.asc())
            else:
                query = query.order_by(
                    Transaction.transaction_date.desc(), Transaction.id.desc()
                )

            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()
            return TransactionListResponse(
                items=[self._to_response(txn) for txn in items],
                total_count=total_count,
                page=page,
                page_size=page_size,
            )

        # type is None (Tất cả): kết hợp giao dịch thu chi và biến động hũ tiết kiệm
        txn_items = [self._to_response(txn) for txn in query.all()]
        saving_items = self._get_saving_responses(
            search=search,
            date_start=date_start,
            date_end=date_end,
            amount_min=amount_min,
            amount_max=amount_max,
            category_id=category_id,
            payment_method=payment_method,
        )
        combined = txn_items + saving_items
        total_count = len(combined)

        if sort == "date_asc":
            combined.sort(key=_sort_key)
        elif sort == "amount_desc":
            combined.sort(key=lambda x: x.amount, reverse=True)
        elif sort == "amount_asc":
            combined.sort(key=lambda x: x.amount)
        else:
            combined.sort(key=_sort_key, reverse=True)

        offset = (page - 1) * page_size
        return TransactionListResponse(
            items=combined[offset : offset + page_size],
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def list_trash(
        self,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort: TransactionSort = "date_desc",
    ) -> TransactionListResponse:
        query = self.db.query(Transaction).filter(
            Transaction.user_id == self.user.id,
            Transaction.is_deleted.is_(True),
        )
        total_count = query.count()

        if sort == "date_asc":
            query = query.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
        elif sort == "amount_desc":
            query = query.order_by(Transaction.amount.desc(), Transaction.id.desc())
        elif sort == "amount_asc":
            query = query.order_by(Transaction.amount.asc(), Transaction.id.asc())
        else:
            query = query.order_by(
                Transaction.transaction_date.desc(), Transaction.id.desc()
            )

        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return TransactionListResponse(
            items=[self._to_response(txn) for txn in items],
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def get_summary(self) -> TransactionSummaryResponse:
        today = local_today()
        first_of_month = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        last_of_month = today.replace(day=last_day)

        all_time_stats = (
            self.db.query(
                Transaction.type,
                sa_func.coalesce(sa_func.sum(Transaction.amount), 0).label("total"),
            )
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.is_deleted.is_(False),
            )
            .group_by(Transaction.type)
            .all()
        )
        all_time_income = Decimal("0.00")
        all_time_expense = Decimal("0.00")
        for txn_type, total in all_time_stats:
            if txn_type == CategoryType.INCOME:
                all_time_income = Decimal(total).quantize(Decimal("0.01"))
            elif txn_type == CategoryType.EXPENSE:
                all_time_expense = Decimal(total).quantize(Decimal("0.01"))

        month_stats = (
            self.db.query(
                Transaction.type,
                sa_func.coalesce(sa_func.sum(Transaction.amount), 0).label("total"),
            )
            .filter(
                Transaction.user_id == self.user.id,
                Transaction.is_deleted.is_(False),
                Transaction.transaction_date >= first_of_month,
                Transaction.transaction_date <= last_of_month,
            )
            .group_by(Transaction.type)
            .all()
        )
        month_income = Decimal("0.00")
        month_expense = Decimal("0.00")
        for txn_type, total in month_stats:
            if txn_type == CategoryType.INCOME:
                month_income = Decimal(total).quantize(Decimal("0.01"))
            elif txn_type == CategoryType.EXPENSE:
                month_expense = Decimal(total).quantize(Decimal("0.01"))

        saving_balance_raw = (
            self.db.query(sa_func.coalesce(sa_func.sum(SavingGoal.current_amount), 0))
            .filter(
                SavingGoal.user_id == self.user.id,
                SavingGoal.status != GoalStatus.CANCELLED,
            )
            .scalar()
        )
        saving_balance = Decimal(str(saving_balance_raw)).quantize(Decimal("0.01"))

        total_balance = all_time_income - all_time_expense
        available_balance = total_balance - saving_balance
        month_net = month_income - month_expense

        return TransactionSummaryResponse(
            total_balance=total_balance,
            available_balance=available_balance,
            saving_balance=saving_balance,
            all_time_income=all_time_income,
            all_time_expense=all_time_expense,
            month_income=month_income,
            month_expense=month_expense,
            month_net=month_net,
        )

    def get_transaction(self, transaction_id: int) -> TransactionResponse:
        txn = self._owned_transaction_or_404(transaction_id)
        return self._to_response(txn)

    def update_transaction(
        self, transaction_id: int, payload: TransactionUpdate
    ) -> TransactionResponse:
        if transaction_id >= 1_000_000_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể chỉnh sửa giao dịch tiết kiệm tại đây. Vui lòng thao tác tại trang Mục tiêu tiết kiệm.",
            )
        self._lock_user_balance()
        txn = self._owned_transaction_or_404(transaction_id)

        changes = payload.model_dump(exclude_unset=True)
        effective_type = changes.get("type", txn.type)
        effective_category_id = changes.get("category_id", txn.category_id)
        effective_amount = Decimal(str(changes.get("amount", txn.amount)))

        contributions = (
            self.db.query(SavingContribution)
            .filter(SavingContribution.transaction_id == txn.id)
            .all()
        )
        if contributions:
            total_allocated = sum(Decimal(str(c.amount)) for c in contributions)
            if effective_type == CategoryType.EXPENSE and txn.type == CategoryType.INCOME:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Giao dịch thu nhập này đang trích {total_allocated:,.0f} đ vào mục tiêu tiết kiệm, không thể đổi loại thành chi tiêu.",
                )
            if "amount" in changes and Decimal(str(changes["amount"])) < total_allocated:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Số tiền thu nhập mới ({changes['amount']:,.0f} đ) không thể nhỏ hơn tổng số tiền đã trích vào mục tiêu tiết kiệm ({total_allocated:,.0f} đ).",
                )

        old_effect = self._balance_effect(txn.type, Decimal(str(txn.amount)))
        new_effect = self._balance_effect(effective_type, effective_amount)
        balance_error = "Thay đổi này sẽ làm số dư khả dụng bị âm."
        if (
            txn.type == CategoryType.EXPENSE
            and effective_type == CategoryType.EXPENSE
            and effective_amount > Decimal(str(txn.amount))
        ):
            balance_error = "Số tiền chi tiêu tăng thêm vượt quá số dư khả dụng hiện có."
        self._ensure_projected_balance(new_effect - old_effect, balance_error)

        if "category_id" in changes or "type" in changes:
            category_is_changing = (
                "category_id" in changes and changes["category_id"] != txn.category_id
            )
            self._validate_category(
                effective_category_id,
                effective_type,
                require_active=category_is_changing,
            )

        for field, value in changes.items():
            setattr(txn, field, value)

        self._commit_or_raise()
        self.db.refresh(txn)

        if txn.type == CategoryType.EXPENSE:
            try:
                from app.services.financial_alert_service import FinancialAlertService
                FinancialAlertService(self.db, self.user).check_and_send_budget_alerts(category_id=txn.category_id, month=txn.transaction_date.month if txn.transaction_date else None, year=txn.transaction_date.year if txn.transaction_date else None)
            except Exception:
                pass

        return self._to_response(txn)

    def trash_transaction(self, transaction_id: int) -> TransactionResponse:
        if transaction_id >= 1_000_000_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể xóa giao dịch tiết kiệm tại đây. Vui lòng thao tác tại trang Mục tiêu tiết kiệm.",
            )
        self._lock_user_balance()
        txn = self._owned_transaction_or_404(transaction_id)

        contributions = (
            self.db.query(SavingContribution)
            .filter(SavingContribution.transaction_id == txn.id)
            .all()
        )
        goal_ids = sorted({contribution.saving_goal_id for contribution in contributions})
        linked_goals = (
            self.db.query(SavingGoal)
            .filter(
                SavingGoal.id.in_(goal_ids),
                SavingGoal.user_id == self.user.id,
            )
            .order_by(SavingGoal.id)
            .with_for_update()
            .all()
            if goal_ids
            else []
        )
        projected_goal_amounts = {
            goal.id: self._recomputed_goal_current_amount(
                goal.id,
                exclude_transaction_id=txn.id,
            )
            for goal in linked_goals
        }
        released_savings = sum(
            (
                Decimal(str(goal.current_amount)) - projected_goal_amounts[goal.id]
                for goal in linked_goals
                if goal.status != GoalStatus.CANCELLED
            ),
            Decimal("0"),
        )
        self._ensure_projected_balance(
            -self._balance_effect(txn.type, Decimal(str(txn.amount))) + released_savings,
            "Không thể xóa nguồn thu vì thao tác này sẽ làm số dư khả dụng bị âm.",
        )
        for goal in linked_goals:
            goal.current_amount = projected_goal_amounts[goal.id]
            if goal.status == GoalStatus.COMPLETED and goal.current_amount < goal.target_amount:
                goal.status = GoalStatus.ACTIVE

        txn.is_deleted = True
        txn.deleted_at = datetime.now(timezone.utc)
        self._commit_or_raise()
        self.db.refresh(txn)

        if txn.type == CategoryType.EXPENSE:
            try:
                from app.services.financial_alert_service import FinancialAlertService
                FinancialAlertService(self.db, self.user).check_and_send_budget_alerts(category_id=txn.category_id, month=txn.transaction_date.month if txn.transaction_date else None, year=txn.transaction_date.year if txn.transaction_date else None)
            except Exception:
                pass

        return self._to_response(txn)

    def restore_transaction(self, transaction_id: int) -> TransactionRestoreResponse:
        self._lock_user_balance()
        txn = self._owned_transaction_or_404(transaction_id, include_deleted=True)
        if not txn.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Giao dịch này không nằm trong thùng rác.",
            )

        contributions = (
            self.db.query(SavingContribution)
            .filter(SavingContribution.transaction_id == txn.id)
            .all()
        )
        goal_ids = sorted({contribution.saving_goal_id for contribution in contributions})
        linked_goals = (
            self.db.query(SavingGoal)
            .filter(
                SavingGoal.id.in_(goal_ids),
                SavingGoal.user_id == self.user.id,
            )
            .order_by(SavingGoal.id)
            .with_for_update()
            .all()
            if goal_ids
            else []
        )
        projected_goal_amounts = {
            goal.id: self._recomputed_goal_current_amount(
                goal.id,
                restore_transaction_id=txn.id,
            )
            for goal in linked_goals
        }
        restored_savings = sum(
            (
                projected_goal_amounts[goal.id] - Decimal(str(goal.current_amount))
                for goal in linked_goals
                if goal.status != GoalStatus.CANCELLED
            ),
            Decimal("0"),
        )
        self._ensure_projected_balance(
            self._balance_effect(txn.type, Decimal(str(txn.amount))) - restored_savings,
            (
                "Khôi phục giao dịch chi tiêu sẽ làm số dư khả dụng bị âm."
                if txn.type == CategoryType.EXPENSE
                else "Không thể khôi phục giao dịch vì thao tác này sẽ làm số dư khả dụng bị âm."
            ),
        )
        for goal in linked_goals:
            goal.current_amount = projected_goal_amounts[goal.id]
            if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
                goal.status = GoalStatus.COMPLETED

        warning = None
        category = (
            self.db.query(Category)
            .filter(Category.id == txn.category_id, Category.user_id == self.user.id)
            .first()
        )
        if category and category.deleted_at is not None:
            warning = (
                f'Danh mục "{category.name}" hiện đã xóa. '
                "Giao dịch được khôi phục nhưng bạn nên cập nhật danh mục."
            )
        elif category and not category.is_active:
            warning = (
                f'Danh mục "{category.name}" hiện đã ẩn. '
                "Giao dịch được khôi phục nhưng bạn nên cập nhật danh mục."
            )

        txn.is_deleted = False
        txn.deleted_at = None
        self._commit_or_raise()
        self.db.refresh(txn)
        return TransactionRestoreResponse(
            transaction=self._to_response(txn),
            category_warning=warning,
        )

    def delete_permanently(self, transaction_id: int) -> None:
        txn = self._owned_transaction_or_404(transaction_id, include_deleted=True)
        if not txn.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Giao dịch phải ở trong thùng rác trước khi xóa vĩnh viễn.",
            )
        self.db.query(SavingContribution).filter(
            SavingContribution.transaction_id == txn.id
        ).delete(synchronize_session=False)

        self.db.delete(txn)
        self._commit_or_raise()

    def duplicate_transaction(self, transaction_id: int) -> TransactionResponse:
        if transaction_id >= 1_000_000_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể nhân bản giao dịch tiết kiệm.",
            )
        txn = self._owned_transaction_or_404(transaction_id)
        return self._to_response(txn)
