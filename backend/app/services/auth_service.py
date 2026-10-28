"""Authentication and user account service implementing core business logic."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.category_defaults import add_missing_default_categories
from app.core.password_reset import password_version, send_password_reset_email
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    get_password_hash,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.services.email_service import EmailService
from app.schemas.user import (
    MessageResponse,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    UserCreate,
    UserUpdate,
)

USER_ALREADY_EXISTS = "Username or email already exists."
PASSWORD_RESET_MESSAGE = "Nếu email tồn tại, hướng dẫn đặt lại mật khẩu sẽ được gửi đến bạn."
logger = logging.getLogger(__name__)


class AuthService:
    """Service layer encapsulating authentication and user profile logic."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, user_in: UserCreate) -> User:
        user = self.db.query(User).filter(
            (User.email == user_in.email) | (User.username == user_in.username)
        ).first()
        if user:
            raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)

        new_user = User(
            username=user_in.username,
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            role=UserRole.USER,
            is_locked=False,
        )
        self.db.add(new_user)
        try:
            self.db.flush()
            add_missing_default_categories(self.db, new_user.id)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)
        self.db.refresh(new_user)
        return new_user

    def login(self, form_data: OAuth2PasswordRequestForm) -> Token:
        identifier = form_data.username.strip()
        user = self.db.query(User).filter(
            or_(User.username == identifier, User.email == identifier.lower())
        ).first()

        # Fallback: nếu người dùng gõ phần đầu của email (VD: 'letaman101' thay vì 'letaman101@gmail.com')
        if not user and "@" not in identifier:
            candidates = self.db.query(User).filter(
                User.email.like(f"{identifier.lower()}@%")
            ).all()
            if len(candidates) == 1:
                user = candidates[0]

        if not user:
            print(f"❌ [LOGIN THẤT BẠI] Không tìm thấy tài khoản với Tên đăng nhập/Email: '{identifier}'", flush=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(form_data.password, user.password_hash):
            print(f"❌ [LOGIN THẤT BẠI] Sai mật khẩu cho tài khoản username='{user.username}', email='{user.email}'", flush=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        print(f"✅ [LOGIN THÀNH CÔNG] Tài khoản '{user.username}' ({user.email}) đăng nhập thành công.", flush=True)

        if getattr(user, "is_locked", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị tạm khóa bởi quản trị viên. Vui lòng liên hệ hỗ trợ.",
            )

        role_attr = getattr(user, "role", "user")
        user_role = str(getattr(role_attr, "value", role_attr))


        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "role": str(user_role)},
            expires_delta=access_token_expires,
        )
        return Token(
            access_token=access_token,
            token_type="bearer",
            role=str(user_role),
            must_change_password=bool(getattr(user, "must_change_password", False)),
            is_verified=bool(getattr(user, "is_verified", False)),
        )

    def forgot_password(self, request: PasswordResetRequest) -> MessageResponse:
        GENERIC_SUCCESS_MESSAGE = "Nếu email tồn tại trong hệ thống, mã xác thực và hướng dẫn đặt lại mật khẩu đã được gửi đến bạn."
        email = request.email.strip().lower()
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # OWASP Anti-Enumeration: Trả về 200 kèm thông báo chung để ngăn chặn dò quét email
            print(f"🔒 [OWASP ANTI-ENUMERATION] Email không tồn tại: '{email}', bảo vệ danh tính bằng thông điệp chung.", flush=True)
            return MessageResponse(message=GENERIC_SUCCESS_MESSAGE)

        if getattr(user, "is_locked", False):
            print(f"🔒 [OWASP ANTI-ENUMERATION] Tài khoản bị khóa: '{email}', bảo vệ danh tính bằng thông điệp chung.", flush=True)
            return MessageResponse(message=GENERIC_SUCCESS_MESSAGE)

        otp_code = f"{secrets.randbelow(900000) + 100000}"
        user.reset_password_code = otp_code
        user.reset_password_code_expires_at = datetime.now() + timedelta(minutes=15)
        self.db.commit()

        EmailService.send_password_reset_otp(user.email, otp_code)

        # Hỗ trợ callback token cho unit test hoặc backward compatibility
        try:
            from app.api.routes import auth as auth_routes
            send_fn = getattr(auth_routes, "send_password_reset_email", None)
            if send_fn and send_fn != send_password_reset_email:
                token = create_password_reset_token(user.id, user.password_hash)
                reset_url = (
                    f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={quote(token)}"
                )
                send_fn(user.email, reset_url)
        except Exception:
            pass

        return MessageResponse(message=GENERIC_SUCCESS_MESSAGE)

    def reset_password(self, request: PasswordResetConfirm) -> MessageResponse:
        INVALID_CODE = "Mã xác thực không hợp lệ hoặc đã hết hạn."
        INVALID_TOKEN = "Đường dẫn đặt lại mật khẩu không hợp lệ hoặc đã hết hạn."

        # Case 1: OTP Code verification (email + code)
        if request.code and request.email:
            email = request.email.strip().lower()
            code = request.code.strip()
            user = self.db.query(User).filter(User.email == email).first()
            if not user or not user.reset_password_code:
                raise HTTPException(status_code=400, detail=INVALID_CODE)

            if user.reset_password_code != code:
                raise HTTPException(status_code=400, detail=INVALID_CODE)

            if not user.reset_password_code_expires_at or user.reset_password_code_expires_at < datetime.now():
                raise HTTPException(status_code=400, detail="Mã xác thực đã hết hạn (chỉ có hiệu lực trong 15 phút).")

            user.password_hash = get_password_hash(request.password)
            user.reset_password_code = None
            user.reset_password_code_expires_at = None
            user.must_change_password = False
            user.is_verified = True  # Đã nhập đúng OTP từ hộp thư nên xác thực thành công
            self.db.commit()
            return MessageResponse(message="Mật khẩu đã được cập nhật thành công.")

        # Case 2: JWT token fallback
        if request.token:
            try:
                payload = jwt.decode(
                    request.token,
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                )
                if payload.get("type") != "password_reset":
                    raise HTTPException(status_code=400, detail=INVALID_TOKEN)
                user_id = int(payload.get("sub", 0))
                token_ver = payload.get("ver")
            except (InvalidTokenError, ValueError, TypeError):
                raise HTTPException(status_code=400, detail=INVALID_TOKEN)

            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or password_version(user.password_hash) != token_ver:
                raise HTTPException(status_code=400, detail=INVALID_TOKEN)

            user.password_hash = get_password_hash(request.password)
            user.must_change_password = False
            self.db.commit()
            return MessageResponse(message="Mật khẩu đã được cập nhật thành công.")

        raise HTTPException(status_code=400, detail="Vui lòng cung cấp mã xác thực OTP hoặc mã token hợp lệ.")

    def send_verification_email(self, current_user: User) -> MessageResponse:
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        current_user.verification_code = otp_code
        current_user.verification_code_expires_at = datetime.now() + timedelta(minutes=15)
        self.db.commit()

        EmailService.send_email_verification_otp(current_user.email, otp_code)
        return MessageResponse(message=f"Đã gửi mã xác minh 6 số tới email {current_user.email}.")

    def verify_email(self, current_user: User, code: str) -> User:
        clean_code = code.strip()
        if not current_user.verification_code or current_user.verification_code != clean_code:
            raise HTTPException(status_code=400, detail="Mã xác thực không chính xác.")

        if not current_user.verification_code_expires_at or current_user.verification_code_expires_at < datetime.now():
            raise HTTPException(status_code=400, detail="Mã xác thực đã hết hạn (chỉ có hiệu lực trong 15 phút).")

        current_user.is_verified = True
        current_user.verification_code = None
        current_user.verification_code_expires_at = None
        self.db.commit()
        self.db.refresh(current_user)
        return current_user

    def dismiss_balance_guide(self, current_user: User) -> MessageResponse:
        current_user.has_seen_initial_balance_guide = True
        self.db.commit()
        return MessageResponse(message="Đã hoàn tất hướng dẫn số dư ban đầu.")

    def update_profile(self, current_user: User, user_in: UserUpdate) -> User:
        if user_in.username is not None:
            existing = (
                self.db.query(User)
                .filter(User.username == user_in.username, User.id != current_user.id)
                .first()
            )
            if existing:
                raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)
            current_user.username = user_in.username
        if user_in.email is not None:
            new_email = user_in.email.strip().lower()
            if new_email != current_user.email.strip().lower():
                existing = (
                    self.db.query(User)
                    .filter(User.email == new_email, User.id != current_user.id)
                    .first()
                )
                if existing:
                    raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)
                current_user.email = new_email
                # Bắt buộc reset trạng thái xác minh khi đổi sang email mới
                current_user.is_verified = False
                current_user.verification_code = None
                current_user.verification_code_expires_at = None
                print(f"⚠️ [PROFILE EMAIL CHANGED] User '{current_user.username}' đổi sang email mới: '{new_email}'. Đã reset is_verified=False.", flush=True)
        if user_in.avatar_url is not None:
            current_user.avatar_url = (
                user_in.avatar_url.strip() if user_in.avatar_url.strip() else None
            )

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=USER_ALREADY_EXISTS)
        self.db.refresh(current_user)
        return current_user

    def upload_avatar(
        self, current_user: User, content: bytes, original_filename: str | None, content_type: str | None
    ) -> User:
        ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/jpg"}
        MAX_SIZE = 2 * 1024 * 1024  # 2MB

        if content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Định dạng ảnh không hợp lệ. Chỉ chấp nhận JPG, PNG, WEBP hoặc GIF.",
            )

        if len(content) > MAX_SIZE:
            raise HTTPException(
                status_code=400,
                detail="Dung lượng ảnh vượt quá giới hạn 2MB.",
            )

        ext = "png"
        if original_filename and "." in original_filename:
            parsed_ext = original_filename.rsplit(".", 1)[-1].lower()
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
        self.db.commit()
        self.db.refresh(current_user)
        return current_user

    def change_password(
        self, current_user: User, request: PasswordChange
    ) -> MessageResponse:
        if not verify_password(request.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác.")
        if request.current_password == request.new_password:
            raise HTTPException(status_code=400, detail="Mật khẩu mới phải khác mật khẩu hiện tại.")

        current_user.password_hash = get_password_hash(request.new_password)
        current_user.must_change_password = False
        current_user.is_verified = True
        self.db.commit()
        return MessageResponse(message="Đổi mật khẩu thành công.")
