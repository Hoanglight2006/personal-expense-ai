"""Admin service implementing business logic for user management and system monitoring."""

from __future__ import annotations

import secrets
import string
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.category_defaults import add_missing_default_categories
from app.core.security import get_password_hash
from app.models.ai_report import AIReport
from app.models.enums import UserRole
from app.models.transaction import Transaction
from app.models.user import User
from app.services.email_service import EmailService
from app.schemas.admin import (
    AdminCreateUserRequest,
    AdminResetPasswordResponse,
    AdminSystemStatsResponse,
    AdminUserItem,
    AdminUserListResponse,
)


class AdminService:
    """Encapsulates administrative functions: user management, security enforcement, and telemetry."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_users(
        self,
        search: Optional[str] = None,
        status_filter: str = "all",
        skip: int = 0,
        limit: int = 50,
    ) -> AdminUserListResponse:
        query = self.db.query(User)

        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(or_(func.lower(User.username).like(s), func.lower(User.email).like(s)))

        if status_filter == "active":
            query = query.filter(User.is_locked.is_(False))
        elif status_filter == "locked":
            query = query.filter(User.is_locked.is_(True))

        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

        # Count active and locked across the entire database
        total_active = self.db.query(func.count(User.id)).filter(User.is_locked.is_(False)).scalar() or 0
        total_locked = self.db.query(func.count(User.id)).filter(User.is_locked.is_(True)).scalar() or 0

        # Subquery for transaction counts per user
        user_ids = [u.id for u in users]
        txn_counts: dict[int, int] = {}
        if user_ids:
            counts = (
                self.db.query(Transaction.user_id, func.count(Transaction.id))
                .filter(Transaction.user_id.in_(user_ids), Transaction.is_deleted.is_(False))
                .group_by(Transaction.user_id)
                .all()
            )
            txn_counts = {uid: count for uid, count in counts}

        items = [
            AdminUserItem(
                id=u.id,
                username=u.username,
                email=u.email,
                avatar_url=u.avatar_url,
                role=str(getattr(u.role, "value", u.role)),
                is_locked=bool(u.is_locked),
                created_at=u.created_at,
                transaction_count=txn_counts.get(u.id, 0),
            )
            for u in users
        ]

        return AdminUserListResponse(
            items=items,
            total=total,
            active_count=total_active,
            locked_count=total_locked,
        )

    def toggle_user_status(
        self,
        user_id: int,
        is_locked: bool,
        current_admin_id: int,
    ) -> AdminUserItem:
        if user_id == current_admin_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bạn không thể tự khóa tài khoản quản trị của chính mình.",
            )

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại.")

        user.is_locked = is_locked
        self.db.commit()
        self.db.refresh(user)

        txn_count = (
            self.db.query(func.count(Transaction.id))
            .filter(Transaction.user_id == user.id, Transaction.is_deleted.is_(False))
            .scalar()
            or 0
        )

        return AdminUserItem(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            role=str(getattr(user.role, "value", user.role)),
            is_locked=bool(user.is_locked),
            created_at=user.created_at,
            transaction_count=txn_count,
        )

    def reset_user_password(
        self,
        user_id: int,
        current_admin_id: int,
    ) -> AdminResetPasswordResponse:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại.")

        # Generate a safe random 10-char temporary password (e.g. Reset@Ab12)
        digits = "".join(secrets.choice(string.digits) for _ in range(4))
        letters = "".join(secrets.choice(string.ascii_letters) for _ in range(4))
        temp_password = f"Reset@{letters}{digits}"

        user.password_hash = get_password_hash(temp_password)
        # If user was locked due to password attempts, reset also unlocks account
        user.is_locked = False
        user.must_change_password = True
        self.db.commit()

        return AdminResetPasswordResponse(
            message=f"Đã đặt lại mật khẩu tạm thời thành công cho tài khoản {user.email}.",
            user_id=user.id,
            email=user.email,
            temp_password=temp_password,
        )

    def create_user(self, payload: AdminCreateUserRequest) -> AdminUserItem:
        email = payload.email.strip().lower()
        username = payload.username.strip()

        # Check existing email
        if self.db.query(User).filter(func.lower(User.email) == email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{email}' đã được sử dụng bởi một tài khoản khác.",
            )

        # Check existing username
        if self.db.query(User).filter(func.lower(User.username) == username.lower()).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tên người dùng '{username}' đã tồn tại trong hệ thống.",
            )

        new_user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(payload.password),
            role=payload.role,
            is_locked=False,
            is_verified=False,
            must_change_password=True,
            has_seen_initial_balance_guide=False,
            avatar_url="/static/avatars/default_avatar.png",
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        # Initialize default categories for regular users
        if payload.role == UserRole.USER:
            add_missing_default_categories(self.db, new_user.id)
            self.db.commit()

        # Dispatch welcome & activation email
        try:
            role_val = str(payload.role.value if hasattr(payload.role, "value") else payload.role)
            EmailService.send_account_activation(
                to_email=new_user.email,
                username=new_user.username,
                temp_password=payload.password,
                role=role_val,
            )
        except Exception:
            pass

        return AdminUserItem(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            avatar_url=new_user.avatar_url,
            role=str(getattr(new_user.role, "value", new_user.role)),
            is_locked=bool(new_user.is_locked),
            created_at=new_user.created_at,
            transaction_count=0,
        )

    def get_system_stats(self) -> AdminSystemStatsResponse:
        total_users = self.db.query(func.count(User.id)).scalar() or 0
        active_users = self.db.query(func.count(User.id)).filter(User.is_locked.is_(False)).scalar() or 0
        locked_users = self.db.query(func.count(User.id)).filter(User.is_locked.is_(True)).scalar() or 0
        total_transactions = (
            self.db.query(func.count(Transaction.id)).filter(Transaction.is_deleted.is_(False)).scalar() or 0
        )
        total_ai_reports = self.db.query(func.count(AIReport.id)).scalar() or 0

        # AI report distribution
        reports = (
            self.db.query(AIReport.report_type, func.count(AIReport.id))
            .group_by(AIReport.report_type)
            .all()
        )
        ai_by_type: dict[str, int] = {
            "monthly_summary": 0,
            "budget_suggestion": 0,
            "chat_answer": 0,
        }
        for r_type, count in reports:
            key = str(getattr(r_type, "value", r_type)).lower()
            ai_by_type[key] = count

        return AdminSystemStatsResponse(
            total_users=total_users,
            active_users=active_users,
            locked_users=locked_users,
            total_transactions=total_transactions,
            total_ai_reports=total_ai_reports,
            ai_reports_by_type=ai_by_type,
        )

