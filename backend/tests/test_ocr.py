import io
from decimal import Decimal
from unittest.mock import patch
import pytest

from app.core.ocr.base import ExtractedTransaction
from app.models.enums import CategoryType, PaymentMethod


from app.api.deps import get_current_user
from app.models.user import User


@pytest.fixture
def mock_user():
    return User(id=1, email="test@example.com")


@pytest.fixture(autouse=True)
def override_auth(mock_user):
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_ocr_extract():
    with patch("app.core.ocr.local_provider.LocalOcrProvider.extract_transaction") as mock:
        yield mock


@pytest.fixture
def mock_ocr_factory():
    with patch("app.api.routes.ocr.get_ocr_provider") as mock_factory:
        yield mock_factory


def test_scan_image_success(client, mock_ocr_factory):
    # Setup mock
    mock_provider = mock_ocr_factory.return_value
    mock_provider.extract_transaction.return_value = ExtractedTransaction(
        amount=Decimal("50000"),
        transaction_date="2026-08-12",
        description="Thanh toán ăn uống",
        type_suggestion=CategoryType.EXPENSE,
        payment_method_suggestion=PaymentMethod.CASH,
        category_id=None,
    )
    
    # Create fake image
    fake_img = b"fake_image_data"
    files = {"file": ("test.jpg", io.BytesIO(fake_img), "image/jpeg")}
    
    resp = client.post("/api/v1/transactions/scan-image", files=files)
    
    assert resp.status_code == 200
    data = resp.json()
    assert str(data["amount"]) == "50000"
    assert data["transaction_date"] == "2026-08-12"
    assert data["description"] == "Thanh toán ăn uống"
    assert data["type"] == "expense"
    assert data["payment_method"] == "cash"


def test_scan_image_invalid_mime_type(client):
    fake_txt = b"fake_text"
    files = {"file": ("test.txt", io.BytesIO(fake_txt), "text/plain")}
    
    resp = client.post("/api/v1/transactions/scan-image", files=files)
    
    assert resp.status_code == 400
    assert "Định dạng ảnh không được hỗ trợ" in resp.json()["detail"]


def test_scan_image_missing_tesseract(client, mock_ocr_factory):
    # Simulate provider throwing RuntimeError because Tesseract is not installed
    mock_provider = mock_ocr_factory.return_value
    mock_provider.extract_transaction.side_effect = RuntimeError("OCR engine chưa được cấu hình. Vui lòng cài đặt Tesseract OCR trên hệ thống.")
    
    fake_img = b"fake_image_data"
    files = {"file": ("test.jpg", io.BytesIO(fake_img), "image/jpeg")}
    
    resp = client.post("/api/v1/transactions/scan-image", files=files)
    
    assert resp.status_code == 500
    assert "OCR engine chưa được cấu hình" in resp.json()["detail"]
