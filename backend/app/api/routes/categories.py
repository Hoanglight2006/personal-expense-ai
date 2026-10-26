"""Category management API routes.

Provides thin HTTP endpoints delegating business logic to CategoryService.
All endpoints enforce ownership via the current JWT user.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategorySort,
    CategoryStatusFilter,
    CategoryUpdate,
)
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Tạo mới một danh mục thu hoặc chi."""
    return CategoryService(db, current_user).create_category(category_in)


@router.post("/defaults", response_model=list[CategoryResponse], status_code=status.HTTP_201_CREATED)
def create_default_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CategoryResponse]:
    """Tạo các danh mục mặc định còn thiếu cho người dùng."""
    return CategoryService(db, current_user).create_defaults()


@router.get("", response_model=CategoryListResponse)
def list_categories(
    search: Annotated[str | None, Query(max_length=50)] = None,
    status_filter: Annotated[CategoryStatusFilter, Query(alias="status")] = "active",
    sort: CategorySort = "amount_desc",
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryListResponse:
    """Lấy danh sách danh mục có thống kê tổng thu/chi trong kỳ."""
    return CategoryService(db, current_user).list_categories(
        search=search,
        status_filter=status_filter,
        sort=sort,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/statistics", response_model=CategoryListResponse)
def category_statistics(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryListResponse:
    """Thống kê chi tiêu theo danh mục (bao gồm cả danh mục ẩn)."""
    return CategoryService(db, current_user).get_statistics(
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Xem chi tiết một danh mục cụ thể và số liệu thống kê."""
    return CategoryService(db, current_user).get_category(
        category_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Cập nhật tên, icon, màu sắc hoặc loại của danh mục."""
    return CategoryService(db, current_user).update_category(category_id, category_in)


@router.post("/{category_id}/hide", response_model=CategoryResponse)
def hide_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Ẩn danh mục khỏi giao diện chọn giao dịch mới."""
    return CategoryService(db, current_user).hide_category(category_id)


@router.post("/{category_id}/restore", response_model=CategoryResponse)
def restore_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Hiện lại danh mục đã bị ẩn."""
    return CategoryService(db, current_user).restore_category(category_id)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Xóa danh mục (xóa mềm để bảo toàn lịch sử giao dịch)."""
    CategoryService(db, current_user).delete_category(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
