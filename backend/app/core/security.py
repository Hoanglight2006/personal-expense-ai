from datetime import datetime, timedelta, timezone
import hashlib
from typing import Optional

import bcrypt
import jwt

from app.config import settings


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    if len(plain_password.encode("utf-8")) > 72:
        return False
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_password_reset_token(user_id: int, password_hash: str) -> str:
    expires_delta = timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "password_reset",
        "ver": hashlib.sha256(password_hash.encode("utf-8")).hexdigest(),
    }
    return create_access_token(payload, expires_delta=expires_delta)
