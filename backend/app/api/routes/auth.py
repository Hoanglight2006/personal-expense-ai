"""Authentication and user management API routes.

Provides thin HTTP endpoints delegating business logic to AuthService.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.password_reset import send_password_reset_email
from app.models.user import User
from app.schemas.user import (
    EmailVerifyRequest,
    MessageResponse,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """Đăng ký tài khoản người dùng mới và tạo danh mục mặc định."""
    return AuthService(db).register(user_in)


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """Đăng nhập bằng username/email và mật khẩu, trả về JWT Access Token."""
    return AuthService(db).login(form_data)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Gửi email yêu cầu đặt lại mật khẩu."""
    return AuthService(db).forgot_password(request)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Đặt lại mật khẩu mới thông qua mã token gửi qua email."""
    return AuthService(db).reset_password(request)


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)) -> Any:
    """Lấy thông tin tài khoản đang đăng nhập."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_users_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Cập nhật thông tin tài khoản (username, email, avatar)."""
    return AuthService(db).update_profile(current_user, user_in)


@router.post("/avatar/upload", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Tải lên ảnh đại diện tùy chỉnh (JPG, PNG, WEBP, GIF, max 2MB)."""
    content = await file.read()
    return AuthService(db).upload_avatar(
        current_user,
        content=content,
        original_filename=file.filename,
        content_type=file.content_type,
    )


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    request: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Đổi mật khẩu tài khoản sau khi xác thực mật khẩu hiện tại."""
    return AuthService(db).change_password(current_user, request)


@router.post("/send-verification-email", response_model=MessageResponse)
def send_verification_email(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Gửi mã OTP xác minh địa chỉ email của người dùng."""
    return AuthService(db).send_verification_email(current_user)


@router.post("/verify-email", response_model=UserResponse)
def verify_email(
    payload: EmailVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Xác minh email người dùng bằng mã OTP 6 số."""
    return AuthService(db).verify_email(current_user, payload.code)


@router.post("/dismiss-balance-guide", response_model=MessageResponse)
def dismiss_balance_guide(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Đánh dấu người dùng đã xem bảng hướng dẫn số dư ban đầu lần đầu truy cập."""
    return AuthService(db).dismiss_balance_guide(current_user)
