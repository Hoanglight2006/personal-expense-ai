from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class AdminCreateUserRequest(BaseModel):
    """Payload to provision a new user or administrator account."""

    username: str = Field(..., min_length=2, max_length=50, description="Tên người dùng")
    email: EmailStr = Field(..., description="Địa chỉ email hợp lệ")
    password: str = Field(..., min_length=6, max_length=100, description="Mật khẩu khởi tạo")
    role: UserRole = Field(default=UserRole.USER, description="Vai trò: user hoặc admin")


class AdminUserItem(BaseModel):
    """User item returned in admin user management list."""

    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    role: str
    is_locked: bool
    created_at: datetime
    transaction_count: int = 0
    transactions_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    """Paginated list of users with summary counts."""

    items: List[AdminUserItem]
    total: int
    active_count: int
    locked_count: int


class AdminStatusUpdate(BaseModel):
    """Payload to lock or unlock a user account."""

    is_locked: bool = Field(..., description="True to lock account, False to activate/unlock")


class AdminResetPasswordResponse(BaseModel):
    """Response when an admin generates a temporary password for a user."""

    message: str
    user_id: int
    email: str
    temp_password: str


class AdminSystemStatsResponse(BaseModel):
    """Overall system and AI usage statistics for admin dashboard."""

    total_users: int
    active_users: int
    locked_users: int
    total_transactions: int
    total_ai_reports: int
    ai_reports_by_type: Dict[str, int]

