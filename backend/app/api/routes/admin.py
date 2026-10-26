"""Admin API routes for user lifecycle management and system monitoring."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.models.user import User
from app.schemas.admin import (
    AdminCreateUserRequest,
    AdminResetPasswordResponse,
    AdminStatusUpdate,
    AdminSystemStatsResponse,
    AdminUserItem,
    AdminUserListResponse,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    search: Annotated[Optional[str], Query(max_length=100)] = None,
    status_filter: Annotated[str, Query(alias="status")] = "all",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> AdminUserListResponse:
    """Lấy danh sách người dùng trong hệ thống (chỉ dành cho Quản trị viên)."""
    return AdminService(db).list_users(
        search=search,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/users",
    response_model=AdminUserItem,
    status_code=status.HTTP_201_CREATED,
    summary="Cấp tài khoản người dùng hoặc quản trị viên mới",
)
def create_user(
    payload: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> AdminUserItem:
    """Cấp tài khoản mới (User hoặc Admin) trực tiếp từ giao diện quản trị viên."""
    return AdminService(db).create_user(payload)


@router.patch("/users/{user_id}/status", response_model=AdminUserItem)
def toggle_user_status(
    user_id: int,
    payload: AdminStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> AdminUserItem:
    """Khóa hoặc mở khóa tài khoản người dùng."""
    return AdminService(db).toggle_user_status(
        user_id=user_id,
        is_locked=payload.is_locked,
        current_admin_id=current_admin.id,
    )


@router.post("/users/{user_id}/reset-password", response_model=AdminResetPasswordResponse)
def reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> AdminResetPasswordResponse:
    """Hỗ trợ đặt lại mật khẩu tạm thời cho người dùng gặp sự cố đăng nhập."""
    return AdminService(db).reset_user_password(
        user_id=user_id,
        current_admin_id=current_admin.id,
    )


@router.get("/stats", response_model=AdminSystemStatsResponse)
def get_system_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> AdminSystemStatsResponse:
    """Thống kê tổng quan hệ thống và mức độ sử dụng AI Gemini."""
    return AdminService(db).get_system_stats()

