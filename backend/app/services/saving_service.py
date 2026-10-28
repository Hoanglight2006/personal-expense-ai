"""Saving goal service implementing core business logic for saving goals, contributions, and withdrawals."""

from __future__ import annotations

from app.core.timezone import local_today
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func as sa_func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.enums import CategoryType, ContributionSource, GoalStatus
from app.models.saving_contribution import SavingContribution
from app.models.saving_goal import SavingGoal
from app.models.saving_withdrawal import SavingWithdrawal
from app.models.saving_withdrawal_allocation import SavingWithdrawalAllocation
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.saving_goal import (
    SavingContributionCreate,
    SavingContributionResponse,
    SavingGoalCreate,
    SavingGoalListResponse,
    SavingGoalResponse,
    SavingGoalUpdate,
    SavingWithdrawalCreate,
    SavingWithdrawalResponse,
)

GOAL_NOT_FOUND = "Không tìm thấy mục tiêu tiết kiệm."


class SavingService:
    """Service layer encapsulating saving goal business logic."""

    def __init__(self, db: Session, current_user: User) -> None:
        self.db = db
        self.user = current_user

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _lock_user_balance(self) -> None:
        """Serialize every balance-changing operation for the user."""
        self.db.query(User.id).filter(User.id == self.user.id).with_for_update().one()

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

    def _get_goal_or_404(self, goal_id: int, *, lock: bool = False) -> SavingGoal:
        query = (
            self.db.query(SavingGoal)
            .options(
                selectinload(SavingGoal.contributions),
                selectinload(SavingGoal.withdrawals),
            )
            .filter(SavingGoal.id == goal_id, SavingGoal.user_id == self.user.id)
        )
        if lock:
            query = query.with_for_update()
        goal = query.first()
        if goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=GOAL_NOT_FOUND,
            )
        return goal

    def _enrich_goal_response(self, goal: SavingGoal) -> SavingGoalResponse:
        target = Decimal(str(goal.target_amount))
        current = Decimal(str(goal.current_amount))

        progress = 0.0
        if target > Decimal("0"):
            calc = (current / target) * 100
            if current < target:
                progress = min(99.9, float(round(calc, 1)))
            else:
                progress = float(round(calc, 1))

        remaining = max(Decimal("0.00"), target - current)

        days_left: int | None = None
        if goal.deadline is not None:
            days_left = (goal.deadline - local_today()).days

        sorted_contributions = sorted(
            goal.contributions,
            key=lambda c: c.created_at,
            reverse=True,
        )
        contrib_responses = [
            SavingContributionResponse.model_validate(c) for c in sorted_contributions
        ]
        sorted_withdrawals = sorted(
            goal.withdrawals,
            key=lambda withdrawal: withdrawal.created_at,
            reverse=True,
        )
        withdrawal_responses = [
            SavingWithdrawalResponse.model_validate(withdrawal)
            for withdrawal in sorted_withdrawals
        ]

        return SavingGoalResponse(
            id=goal.id,
            user_id=goal.user_id,
            name=goal.name,
            target_amount=target,
            current_amount=current,
            deadline=goal.deadline,
            status=goal.status,
            progress_percentage=progress,
            remaining_amount=remaining,
            days_remaining=days_left,
            contributions=contrib_responses,
            withdrawals=withdrawal_responses,
            created_at=goal.created_at,
        )

    # -----------------------------------------------------------------------
    # Public Business Methods
    # -----------------------------------------------------------------------

    def create_goal(self, payload: SavingGoalCreate) -> SavingGoalResponse:
        self._lock_user_balance()
        initial_deposit = payload.initial_deposit or Decimal("0")
        if initial_deposit > Decimal("0"):
            available_balance = self._get_user_available_balance()
            if initial_deposit > available_balance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Số tiền nạp ban đầu ({initial_deposit:,.0f} đ) vượt quá số dư khả dụng hiện có ({available_balance:,.0f} đ).",
                )

        initial_status = GoalStatus.ACTIVE
        if initial_deposit >= payload.target_amount:
            initial_status = GoalStatus.COMPLETED

        goal = SavingGoal(
            user_id=self.user.id,
            name=payload.name.strip(),
            target_amount=payload.target_amount,
            current_amount=initial_deposit,
            deadline=payload.deadline,
            status=initial_status,
        )
        self.db.add(goal)
        self.db.flush()

        if initial_deposit > Decimal("0"):
            contribution = SavingContribution(
                saving_goal_id=goal.id,
                amount=initial_deposit,
                source=ContributionSource.MANUAL,
                note="Khoản nạp ban đầu",
            )
            self.db.add(contribution)

        self.db.commit()
        self.db.refresh(goal)
        return self._enrich_goal_response(goal)

    def list_goals(
        self, *, status_filter: GoalStatus | None = None
    ) -> SavingGoalListResponse:
        all_goals = (
            self.db.query(SavingGoal)
            .options(
                selectinload(SavingGoal.contributions),
                selectinload(SavingGoal.withdrawals),
            )
            .filter(SavingGoal.user_id == self.user.id)
            .order_by(desc(SavingGoal.created_at))
            .all()
        )

        total_target = Decimal("0.00")
        total_current = Decimal("0.00")
        active_count = 0
        completed_count = 0

        for g in all_goals:
            if g.status != GoalStatus.CANCELLED:
                total_target += Decimal(str(g.target_amount))
                total_current += Decimal(str(g.current_amount))
            if g.status == GoalStatus.ACTIVE:
                active_count += 1
            elif g.status == GoalStatus.COMPLETED:
                completed_count += 1

        filtered_goals = all_goals
        if status_filter is not None:
            filtered_goals = [g for g in all_goals if g.status == status_filter]

        items = [self._enrich_goal_response(g) for g in filtered_goals]

        return SavingGoalListResponse(
            total_target_amount=total_target,
            total_current_amount=total_current,
            total_goals_count=len(all_goals),
            active_goals_count=active_count,
            completed_goals_count=completed_count,
            items=items,
        )

    def get_goal(self, goal_id: int) -> SavingGoalResponse:
        goal = self._get_goal_or_404(goal_id)
        return self._enrich_goal_response(goal)

    def update_goal(
        self, goal_id: int, payload: SavingGoalUpdate
    ) -> SavingGoalResponse:
        self._lock_user_balance()
        goal = self._get_goal_or_404(goal_id, lock=True)


        if payload.name is not None:
            name_val = payload.name.strip()
            if not name_val:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tên mục tiêu không được để trống.",
                )
            goal.name = name_val

        if payload.target_amount is not None:
            goal.target_amount = payload.target_amount
            if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
                goal.status = GoalStatus.COMPLETED
            elif (
                goal.current_amount < goal.target_amount
                and goal.status == GoalStatus.COMPLETED
                and payload.status is None
            ):
                goal.status = GoalStatus.ACTIVE

        if payload.deadline is not None:
            goal.deadline = payload.deadline

        if payload.status is not None:
            if (
                goal.status == GoalStatus.CANCELLED
                and payload.status != GoalStatus.CANCELLED
            ):
                available_balance = self._get_user_available_balance()
                if Decimal(str(goal.current_amount)) > available_balance:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Không thể kích hoạt lại mục tiêu vì số tiền đang tích lũy "
                            "vượt quá số dư khả dụng hiện có."
                        ),
                    )
            goal.status = payload.status

        self.db.commit()
        self.db.refresh(goal)
        return self._enrich_goal_response(goal)

    def contribute(
        self, goal_id: int, payload: SavingContributionCreate
    ) -> SavingGoalResponse:
        self._lock_user_balance()
        goal = self._get_goal_or_404(goal_id, lock=True)


        if goal.status == GoalStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể nạp tiền vào mục tiêu đã bị hủy hoặc tạm dừng.",
            )


        available_balance = self._get_user_available_balance()
        if payload.amount > available_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số tiền nạp ({payload.amount:,.0f} đ) vượt quá số dư khả dụng hiện có ({available_balance:,.0f} đ).",
            )

        contribution = SavingContribution(
            saving_goal_id=goal.id,
            transaction_id=None,
            amount=payload.amount,
            source=ContributionSource.MANUAL,
            note=payload.note.strip() if payload.note else None,
        )
        self.db.add(contribution)

        new_amount = Decimal(str(goal.current_amount)) + payload.amount
        goal.current_amount = new_amount

        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED

        self.db.commit()
        self.db.refresh(goal)
        return self._enrich_goal_response(goal)

    def withdraw(
        self, goal_id: int, payload: SavingWithdrawalCreate
    ) -> SavingGoalResponse:
        self._lock_user_balance()
        goal = self._get_goal_or_404(goal_id, lock=True)
        request_note = payload.note.strip() if payload.note else None

        existing_withdrawal = (
            self.db.query(SavingWithdrawal)
            .filter(
                SavingWithdrawal.saving_goal_id == goal.id,
                SavingWithdrawal.idempotency_key == payload.idempotency_key,
            )
            .first()
        )
        if goal.status == GoalStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mục tiêu đã bị hủy hoặc tạm dừng, số tiền đã được hoàn trả về số dư khả dụng.",
            )

        if existing_withdrawal is not None:
            if (
                Decimal(str(existing_withdrawal.amount)) != payload.amount
                or existing_withdrawal.note != request_note
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Khóa rút tiền này đã được dùng với nội dung khác.",
                )
            return self._enrich_goal_response(goal)

        current_amount = Decimal(str(goal.current_amount))
        if current_amount <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mục tiêu chưa có tiền để rút.",
            )
        if payload.amount > current_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Số tiền rút ({payload.amount:,.0f} đ) vượt quá số tiền đang "
                    f"tích lũy ({current_amount:,.0f} đ)."
                ),
            )

        eligible_contributions = (
            self.db.query(SavingContribution)
            .outerjoin(Transaction, Transaction.id == SavingContribution.transaction_id)
            .filter(
                SavingContribution.saving_goal_id == goal.id,
                or_(
                    SavingContribution.source == ContributionSource.MANUAL,
                    and_(
                        SavingContribution.source == ContributionSource.INCOME_ALLOCATION,
                        Transaction.is_deleted.is_(False),
                    ),
                ),
            )
            .order_by(SavingContribution.created_at, SavingContribution.id)
            .all()
        )
        contribution_ids = [contribution.id for contribution in eligible_contributions]
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

        withdrawal = SavingWithdrawal(
            saving_goal=goal,
            amount=payload.amount,
            idempotency_key=payload.idempotency_key,
            note=request_note,
        )
        self.db.add(withdrawal)
        self.db.flush()

        remaining_to_allocate = payload.amount
        for contribution in eligible_contributions:
            already_allocated = allocated_by_contribution.get(
                contribution.id, Decimal("0.00")
            )
            available_from_contribution = max(
                Decimal("0.00"),
                Decimal(str(contribution.amount)) - already_allocated,
            )
            allocated_amount = min(remaining_to_allocate, available_from_contribution)
            if allocated_amount > Decimal("0"):
                self.db.add(
                    SavingWithdrawalAllocation(
                        withdrawal_id=withdrawal.id,
                        contribution_id=contribution.id,
                        amount=allocated_amount,
                    )
                )
                remaining_to_allocate -= allocated_amount
            if remaining_to_allocate == Decimal("0"):
                break

        if remaining_to_allocate > Decimal("0"):
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Lịch sử mục tiêu không khớp với số tiền đang tích lũy. "
                    "Vui lòng tải lại trước khi rút."
                ),
            )
        goal.current_amount = current_amount - payload.amount
        if goal.current_amount < goal.target_amount and goal.status == GoalStatus.COMPLETED:
            goal.status = GoalStatus.ACTIVE

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            goal = self._get_goal_or_404(goal_id)
            existing_withdrawal = (
                self.db.query(SavingWithdrawal)
                .filter(
                    SavingWithdrawal.saving_goal_id == goal.id,
                    SavingWithdrawal.idempotency_key == payload.idempotency_key,
                )
                .first()
            )
            if existing_withdrawal is not None:
                if (
                    Decimal(str(existing_withdrawal.amount)) != payload.amount
                    or existing_withdrawal.note != request_note
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Khóa rút tiền này đã được dùng với nội dung khác.",
                    ) from exc
                return self._enrich_goal_response(goal)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể ghi nhận lần rút tiền do xung đột dữ liệu.",
            ) from exc

        self.db.refresh(goal)
        return self._enrich_goal_response(goal)

    def delete_goal(self, goal_id: int) -> dict[str, str]:
        self._lock_user_balance()
        goal = self._get_goal_or_404(goal_id, lock=True)
        self.db.delete(goal)
        self.db.commit()
        return {"detail": "Đã xóa mục tiêu tiết kiệm thành công."}
