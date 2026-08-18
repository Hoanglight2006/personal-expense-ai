from datetime import datetime
from typing import Optional

import unicodedata

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserBase(BaseModel):
    """Base Pydantic model for User."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    avatar_url: Optional[str] = None

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return unicodedata.normalize("NFKC", value.strip())

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserCreate(UserBase):
    """Model for user registration."""

    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_bcrypt_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return value


class UserUpdate(BaseModel):
    """Editable profile fields for the current user."""

    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return unicodedata.normalize("NFKC", value.strip())

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return value.strip().lower()

    @model_validator(mode="after")
    def require_a_change(self):
        if self.username is None and self.email is None and self.avatar_url is None:
            raise ValueError("At least one profile field is required")
        return self


class PasswordChange(BaseModel):
    """Authenticated password change payload."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

    @field_validator("current_password", "new_password")
    @classmethod
    def validate_bcrypt_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return value


class PasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_reset_email(cls, value: str) -> str:
        return value.strip().lower()


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_reset_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return value


class MessageResponse(BaseModel):
    message: str


class UserResponse(UserBase):
    """Model for returning user data."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Model for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Model for JWT token data."""

    user_id: int
