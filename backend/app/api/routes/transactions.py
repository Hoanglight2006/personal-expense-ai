"""Transaction management API routes.

Provides thin HTTP endpoints delegating business logic to TransactionService.
All endpoints enforce ownership via the current JWT user.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.enums import CategoryType, PaymentMethod
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionRestoreResponse,
    TransactionSort,
    TransactionSummaryResponse,
    TransactionUpdate,
)
from app.services.transaction_service import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    TransactionService,
    _recomputed_goal_current_amount,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Tạo giao dịch thu nhập hoặc chi tiêu mới."""
    return TransactionService(db, current_user).create_transaction(payload)


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    search: Annotated[str | None, Query(max_length=255)] = None,
    date_start: date | None = None,
    date_end: date | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    type: CategoryType | None = None,
    category_id: int | None = None,
    payment_method: PaymentMethod | None = None,
    sort: TransactionSort = "date_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionListResponse:
    """Lấy danh sách giao dịch có phân trang, tìm kiếm và lọc."""
    return TransactionService(db, current_user).list_transactions(
        search=search,
        date_start=date_start,
        date_end=date_end,
        amount_min=amount_min,
        amount_max=amount_max,
        type=type,
        category_id=category_id,
        payment_method=payment_method,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/trash", response_model=TransactionListResponse)
def list_trash(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    sort: TransactionSort = "date_desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionListResponse:
    """Lấy danh sách các giao dịch đã bị xóa tạm (thùng rác)."""
    return TransactionService(db, current_user).list_trash(
        page=page,
        page_size=page_size,
        sort=sort,
    )


@router.get("/summary", response_model=TransactionSummaryResponse)
def get_transaction_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionSummaryResponse:
    """Tổng hợp số liệu tài chính: số dư khả dụng, thu/chi tháng và tích lũy."""
    return TransactionService(db, current_user).get_summary()


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Xem chi tiết một giao dịch cụ thể."""
    return TransactionService(db, current_user).get_transaction(transaction_id)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Cập nhật thông tin giao dịch hiện có."""
    return TransactionService(db, current_user).update_transaction(transaction_id, payload)


@router.post("/{transaction_id}/trash", response_model=TransactionResponse)
def trash_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Chuyển giao dịch vào thùng rác (xóa tạm)."""
    return TransactionService(db, current_user).trash_transaction(transaction_id)


@router.post("/{transaction_id}/restore", response_model=TransactionRestoreResponse)
def restore_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionRestoreResponse:
    """Khôi phục giao dịch từ thùng rác."""
    return TransactionService(db, current_user).restore_transaction(transaction_id)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_transaction_permanently(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Xóa vĩnh viễn giao dịch đã nằm trong thùng rác."""
    TransactionService(db, current_user).delete_permanently(transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{transaction_id}/duplicate", response_model=TransactionResponse)
def duplicate_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Lấy dữ liệu giao dịch mẫu để nhân bản trên form."""
    return TransactionService(db, current_user).duplicate_transaction(transaction_id)
