from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.core.category_suggestion import suggest_category
from app.core.excel.duplicate_detector import is_duplicate_transaction
from app.core.excel.parser_factory import get_excel_parser
from app.models.user import User
from app.schemas.transaction import BulkTransactionRow

router = APIRouter(prefix="/transactions", tags=["excel"])

# Excel can be .xlsx or .xls
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream", # Some browsers send this for excel
}


@router.post("/parse-excel")
async def parse_excel(
    file: Annotated[UploadFile, File(...)],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Parse an Excel statement and return preview data with duplicate checks."""
    if file.content_type not in ALLOWED_MIME_TYPES and not (file.filename and file.filename.endswith(('.xlsx', '.xls'))):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng file không được hỗ trợ. Vui lòng tải lên file Excel (.xlsx, .xls).",
        )

    # Read and check size
    file_bytes = await file.read()
    max_bytes = settings.MAX_EXCEL_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Kích thước file vượt quá {settings.MAX_EXCEL_SIZE_MB}MB.",
        )

    parser = get_excel_parser(file_bytes)
    if not parser:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Định dạng file sao kê không hợp lệ hoặc chưa được hỗ trợ.",
        )

    try:
        rows = parser.parse(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi đọc file Excel: {e}",
        )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Không tìm thấy dữ liệu giao dịch hợp lệ trong file.",
        )

    if len(rows) > 1000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Số lượng giao dịch vượt quá giới hạn (tối đa 1000 dòng).",
        )

    result = []
    for row in rows:
        # Check for duplicate
        is_dup = is_duplicate_transaction(
            db, current_user.id, row.amount, row.transaction_date, row.description
        )

        # Suggest category
        suggested_cat = suggest_category(
            db, current_user.id, row.type, row.description
        )
        cat_id = suggested_cat.id if suggested_cat else None

        result.append({
            "amount": row.amount,
            "type": row.type,
            "category_id": cat_id,
            "transaction_date": row.transaction_date,
            "description": row.description,
            "payment_method": row.payment_method,
            "is_duplicate": is_dup,
        })

    return {"items": result}
