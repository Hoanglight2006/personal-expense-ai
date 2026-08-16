from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.category_suggestion import suggest_category
from app.core.ocr.provider_factory import get_ocr_provider
from app.models.category import Category
from app.models.user import User

router = APIRouter(prefix="/transactions", tags=["ocr"])

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/scan-image")
async def scan_image(
    file: Annotated[UploadFile, File(...)],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scan an invoice/receipt image to extract transaction details."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng ảnh không được hỗ trợ. Chỉ cho phép JPEG, PNG, WebP.",
        )

    # Read and check size
    file_bytes = await file.read()
    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Kích thước ảnh vượt quá {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    provider = get_ocr_provider()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OCR engine chưa được cấu hình.",
        )

    try:
        active_categories = db.query(Category).filter(
            Category.user_id == current_user.id,
            Category.is_active.is_(True),
            Category.deleted_at.is_(None),
        ).all()
        extracted = provider.extract_transaction(file_bytes, active_categories)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý ảnh: {e}",
        )

    category_id = extracted.category_id
    if not category_id and extracted.type_suggestion:
        suggested_cat = suggest_category(
            db, current_user.id, extracted.type_suggestion, extracted.description
        )
        if suggested_cat:
            category_id = suggested_cat.id

    return {
        "amount": extracted.amount,
        "transaction_date": extracted.transaction_date,
        "description": extracted.description,
        "type": extracted.type_suggestion,
        "payment_method": extracted.payment_method_suggestion,
        "category_id": category_id,
    }
