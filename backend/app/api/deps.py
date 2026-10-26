from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """Dependency to get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        role = payload.get("role", "user")
        token_data = TokenData(user_id=int(subject), role=str(role))
    except InvalidTokenError:
        raise credentials_exception
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception

    if getattr(user, "is_locked", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị tạm khóa bởi quản trị viên. Vui lòng liên hệ hỗ trợ.",
        )

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to ensure the current authenticated user has Administrator role."""
    user_role = getattr(current_user, "role", None)
    is_admin = False
    if user_role == UserRole.ADMIN or str(user_role).lower() in ("admin", "userrole.admin"):
        is_admin = True

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yêu cầu quyền Quản trị viên (Admin) để thực hiện thao tác này.",
        )
    return current_user
