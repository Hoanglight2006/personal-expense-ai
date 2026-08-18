from datetime import timedelta
from pathlib import Path
from urllib.parse import quote
from typing import Any
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import InvalidTokenError
import logging

from app.api.deps import get_db, get_current_user
from app.config import settings
from app.core.category_defaults import add_missing_default_categories
from app.core.password_reset import password_version, send_password_reset_email
from app.core.security import create_access_token, create_password_reset_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import (
    MessageResponse,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])
USER_ALREADY_EXISTS = "Username or email already exists."
PASSWORD_RESET_MESSAGE = "Nếu email tồn tại, hướng dẫn đặt lại mật khẩu sẽ được gửi đến bạn."
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Register a new user.
    """
    user = db.query(User).filter(
        (User.email == user_in.email) | (User.username == user_in.username)
    ).first()
    if user:
        raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)

    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
    )
    db.add(user)
    try:
        db.flush()
        add_missing_default_categories(db, user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    identifier = form_data.username.strip()
    user = db.query(User).filter(
        or_(User.username == identifier, User.email == identifier.lower())
    ).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    request: PasswordResetRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    user = db.query(User).filter(User.email == request.email).first()
    if user:
        token = create_password_reset_token(user.id, user.password_hash)
        reset_url = (
            f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={quote(token)}"
        )
        try:
            send_password_reset_email(user.email, reset_url)
        except Exception:
            logger.exception("Password reset email delivery failed")
    return MessageResponse(message=PASSWORD_RESET_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: PasswordResetConfirm, db: Session = Depends(get_db)
) -> MessageResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
    )
    try:
        payload = jwt.decode(
            request.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "password_reset":
            raise credentials_exception
        user_id = int(payload.get("sub"))
        token_version = payload.get("ver")
    except (InvalidTokenError, TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or token_version != password_version(user.password_hash):
        raise credentials_exception

    user.password_hash = get_password_hash(request.password)
    db.commit()
    return MessageResponse(message="Mật khẩu đã được cập nhật. Bạn có thể đăng nhập lại.")


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)) -> Any:
    """
    Get current user details.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_users_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update the current user's public profile fields."""
    duplicate = db.query(User).filter(
        User.id != current_user.id,
        or_(
            User.username == user_in.username if user_in.username is not None else False,
            User.email == user_in.email if user_in.email is not None else False,
        ),
    ).first()
    if duplicate:
        raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)

    if user_in.username is not None:
        current_user.username = user_in.username
    if user_in.email is not None:
        current_user.email = user_in.email
    if user_in.avatar_url is not None:
        current_user.avatar_url = user_in.avatar_url.strip() if user_in.avatar_url.strip() else None

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)
    db.refresh(current_user)
    return current_user


@router.post("/avatar/upload", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Upload a custom avatar image file (JPG, PNG, WEBP, GIF, max 2MB)."""
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/jpg"}
    MAX_SIZE = 2 * 1024 * 1024  # 2MB

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Định dạng ảnh không hợp lệ. Chỉ chấp nhận JPG, PNG, WEBP hoặc GIF.",
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Dung lượng ảnh vượt quá giới hạn 2MB.",
        )

    ext = "png"
    if file.filename and "." in file.filename:
        parsed_ext = file.filename.rsplit(".", 1)[-1].lower()
        if parsed_ext in {"jpg", "jpeg", "png", "webp", "gif"}:
            ext = parsed_ext

    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    upload_dir = Path("static/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    avatar_url = f"/static/avatars/{filename}"
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    request: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Change the current user's password after verifying the old one."""
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác.")
    if request.current_password == request.new_password:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải khác mật khẩu hiện tại.")

    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()
    return MessageResponse(message="Đổi mật khẩu thành công.")

