"""Test suite for AI and Trend Analytics features.

Covers:
- PII masking (STK, card numbers, transaction codes)
- 6-month monthly financial trends
- AI Monthly Report generation and data isolation
- AI Budget Recommendations and 1-click batch application
- FinAI Chat endpoint
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.ai_chat import mask_sensitive_data
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.models.user import User
from tests.test_db import TestingSessionLocal


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------


def create_user_and_auth(client: TestClient, db: Session, email: str = "ai_user@example.com") -> tuple[User, str]:
    """Register and login a test user, returning (user, bearer_token)."""
    username = email.split("@")[0]
    password = "Password123!"
    register_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    assert register_res.status_code == 201
    user_id = register_res.json()["id"]

    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    user = db.query(User).filter(User.id == user_id).first()
    assert user is not None
    return user, token


def create_cat(
    db: Session,
    user_id: int,
    name: str,
    cat_type: CategoryType = CategoryType.EXPENSE,
    icon: str = "utensils",
    color: str = "#FF5722",
) -> Category:
    existing = (
        db.query(Category)
        .filter(Category.user_id == user_id, Category.name_normalized == name.casefold())
        .first()
    )
    if existing:
        return existing
    cat = Category(
        user_id=user_id,
        name=name,
        name_normalized=name.casefold(),
        type=cat_type.value,
        icon=icon,
        color=color,
        is_active=True,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def create_txn(
    db: Session,
    user_id: int,
    category_id: int,
    amount: Decimal,
    txn_type: CategoryType,
    txn_date: date,
    description: str | None = None,
) -> Transaction:
    txn = Transaction(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        type=txn_type,
        transaction_date=txn_date,
        description=description,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


# ---------------------------------------------------------------------------
# 1. PII Masking Tests
# ---------------------------------------------------------------------------


def test_mask_sensitive_data():
    """Verify bank account numbers, card numbers, and banking trans codes are masked."""
    # Test Bank Account Number (8+ consecutive digits)
    text1 = "Chuyển khoản thanh toán tiền phòng STK 09123456789 VCB"
    assert "[STK_ĐÃ_ẨN]" in mask_sensitive_data(text1)
    assert "09123456789" not in mask_sensitive_data(text1)

    # Test Bank Transaction Code (e.g. FT231234567, MB987654)
    text2 = "Mã giao dịch FT23123456789 hoặc MB123456"
    assert "[MÃ_GD_ĐÃ_ẨN]" in mask_sensitive_data(text2)
    assert "FT23123456789" not in mask_sensitive_data(text2)

    # Test Card Number (16 digits with space or hyphen)
    text3 = "Thanh toán thẻ 4111 2222 3333 4444 tại POS"
    assert "[SỐ_THẺ_ĐÃ_ẨN]" in mask_sensitive_data(text3)
    assert "4111 2222 3333 4444" not in mask_sensitive_data(text3)

    # Normal text should remain untouched
    normal = "Ăn tối cùng bạn bè 150k"
    assert mask_sensitive_data(normal) == normal


# ---------------------------------------------------------------------------
# 2. Monthly Trend Analytics Tests
# ---------------------------------------------------------------------------


def test_get_monthly_trend(client: TestClient):
    """Test the 6-month financial trend analytics endpoint."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "trend_user@example.com")
    other_user, _ = create_user_and_auth(client, db, "other_trend_user@example.com")

    # Categories
    cat_salary = create_cat(db, user.id, "Lương", CategoryType.INCOME)
    cat_food = create_cat(db, user.id, "Ăn uống", CategoryType.EXPENSE)
    cat_other = create_cat(db, other_user.id, "Chi tiêu khác", CategoryType.EXPENSE)

    today = date.today()
    # Add transactions for current month
    create_txn(db, user.id, cat_salary.id, Decimal("15000000"), CategoryType.INCOME, today)
    create_txn(db, user.id, cat_food.id, Decimal("5000000"), CategoryType.EXPENSE, today)

    # Add transaction for other user (should NOT leak)
    create_txn(db, other_user.id, cat_other.id, Decimal("99000000"), CategoryType.EXPENSE, today)

    res = client.get(
        "/api/v1/ai/trend?months=6",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["months_count"] == 6
    assert len(data["items"]) == 6
    # Current month should be the last item
    current_item = data["items"][-1]
    assert Decimal(str(current_item["total_income"])) == Decimal("15000000.00")
    assert Decimal(str(current_item["total_expense"])) == Decimal("5000000.00")
    assert Decimal(str(current_item["net_savings"])) == Decimal("10000000.00")
    assert current_item["savings_rate"] == 66.7
    assert current_item["top_category"] == "Ăn uống"
    assert data["active_months_count"] == 1
    assert Decimal(str(data["average_monthly_income"])) == Decimal("15000000.00")
    assert Decimal(str(data["average_monthly_expense"])) == Decimal("5000000.00")
    assert "1/6 tháng" in data["smart_summary"]
    db.close()


# ---------------------------------------------------------------------------
# 3. AI Monthly Report Tests
# ---------------------------------------------------------------------------


def test_generate_monthly_report(client: TestClient):
    """Test generating structured AI monthly report."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "report_user@example.com")

    cat_sal = create_cat(db, user.id, "Thu nhập", CategoryType.INCOME)
    cat_food = create_cat(db, user.id, "Ăn uống", CategoryType.EXPENSE)
    cat_rent = create_cat(db, user.id, "Tiền nhà", CategoryType.EXPENSE)

    today = date.today()
    month_str = f"{today.year:04d}-{today.month:02d}"

    create_txn(db, user.id, cat_sal.id, Decimal("20000000"), CategoryType.INCOME, today)
    create_txn(db, user.id, cat_food.id, Decimal("4000000"), CategoryType.EXPENSE, today)
    create_txn(db, user.id, cat_rent.id, Decimal("6000000"), CategoryType.EXPENSE, today)

    # Set budget for food
    b = Budget(user_id=user.id, category_id=cat_food.id, amount=Decimal("5000000"), month=today.month, year=today.year)
    db.add(b)
    db.commit()

    import json
    with patch("app.core.ai_service.genai.GenerativeModel") as mock_model_cls:
        mock_instance = mock_model_cls.return_value
        mock_res = AsyncMock()
        mock_res.text = json.dumps({
            "overview": "Tình hình tài chính tháng rất khả quan.",
            "trend_analysis": "Chi tiêu tập trung ở tiền nhà và ăn uống.",
            "adjustments": [
                "Giảm bớt ăn ngoài",
                "Tiết kiệm điện nước",
                "Đầu tư thêm quỹ dự phòng",
            ],
            "conclusion": "Cần duy trì phong độ tốt.",
        })
        mock_instance.generate_content_async = AsyncMock(return_value=mock_res)

        res = client.post(
            "/api/v1/ai/monthly-report",
            json={"month": month_str},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    data = res.json()

    assert data["month"] == month_str
    assert 0 <= data["financial_health_score"] <= 100
    assert data["health_status"] in ["Xuất sắc", "Tốt", "Cần chú ý", "Báo động", "Đang theo dõi"]
    assert Decimal(str(data["total_income"])) == Decimal("20000000.00")
    assert Decimal(str(data["total_expense"])) == Decimal("10000000.00")
    assert Decimal(str(data["net_savings"])) == Decimal("10000000.00")
    assert data["savings_rate"] == 50.0
    assert len(data["adjustments"]) >= 1
    assert "Báo Cáo Phân Tích Chi Tiêu" in data["raw_markdown"]
    db.close()

def test_generate_monthly_report_preliminary_and_focus(client: TestClient):
    """Test preliminary status when spending < 500k and different focus options."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "prelim_user@example.com")

    cat_sal = create_cat(db, user.id, "Thu nhập", CategoryType.INCOME)
    cat_coffee = create_cat(db, user.id, "Cà phê", CategoryType.EXPENSE)

    today = date.today()
    month_str = f"{today.year:04d}-{today.month:02d}"

    # Only 80k expense (below 500k threshold)
    create_txn(db, user.id, cat_sal.id, Decimal("5000000"), CategoryType.INCOME, today)
    create_txn(db, user.id, cat_coffee.id, Decimal("80000"), CategoryType.EXPENSE, today)

    # Test saving focus without mock (fallback flow)
    res_saving = client.post(
        "/api/v1/ai/monthly-report",
        json={"month": month_str, "focus": "saving"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_saving.status_code == 200
    data_saving = res_saving.json()
    assert data_saving["health_status"] == "Đang theo dõi"
    assert data_saving["financial_health_score"] == 70
    assert "Tối Ưu Tiết Kiệm" in data_saving["raw_markdown"]

    # Test risk focus
    res_risk = client.post(
        "/api/v1/ai/monthly-report",
        json={"month": month_str, "focus": "risk"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_risk.status_code == 200
    data_risk = res_risk.json()
    assert data_risk["health_status"] == "Đang theo dõi"
    assert "Cảnh Báo Rủi Ro" in data_risk["raw_markdown"]

    db.close()



# ---------------------------------------------------------------------------
# 4. AI Budget Recommendations Tests
# ---------------------------------------------------------------------------


def test_budget_recommendations_and_apply(client: TestClient):
    """Test AI budget suggestions and 1-click application."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "budget_ai_user@example.com")

    cat_food = create_cat(db, user.id, "Ăn uống", CategoryType.EXPENSE)
    cat_shop = create_cat(db, user.id, "Mua sắm", CategoryType.EXPENSE)

    today = date.today()
    # Add historical transactions for food and shopping
    create_txn(db, user.id, cat_food.id, Decimal("3200000"), CategoryType.EXPENSE, today)
    create_txn(db, user.id, cat_shop.id, Decimal("1800000"), CategoryType.EXPENSE, today)

    import json
    with patch("app.core.ai_service.genai.GenerativeModel") as mock_model_cls:
        mock_instance = mock_model_cls.return_value
        mock_res = AsyncMock()
        mock_res.text = json.dumps([
            {"id": cat_food.id, "recommended_amount": 3500000, "reason": "Hạn mức tối ưu dựa trên mức chi trung bình."},
            {"id": cat_shop.id, "recommended_amount": 2000000, "reason": "Duy trì mua sắm trong tầm kiểm soát."},
        ])
        mock_instance.generate_content_async = AsyncMock(return_value=mock_res)

        # 1. Fetch suggestions for next month
        res = client.get(
            "/api/v1/ai/budget-recommendations",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    data = res.json()

    assert len(data["recommendations"]) >= 2
    rec_food = next(r for r in data["recommendations"] if r["category_id"] == cat_food.id)
    assert Decimal(str(rec_food["recommended_amount"])) > Decimal("0")
    assert rec_food["reason"] != ""

    # 2. Apply recommendations
    apply_payload = {
        "target_month": data["target_month"],
        "target_year": data["target_year"],
        "recommendations": [
            {"category_id": cat_food.id, "amount": rec_food["recommended_amount"]},
            {"category_id": cat_shop.id, "amount": 2000000},
        ],
    }

    apply_res = client.post(
        "/api/v1/ai/apply-budget-recommendations",
        json=apply_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert apply_res.status_code == 200
    assert apply_res.json()["applied_count"] == 2

    # Verify budgets are in database
    food_budget = (
        db.query(Budget)
        .filter(
            Budget.user_id == user.id,
            Budget.category_id == cat_food.id,
            Budget.month == data["target_month"],
            Budget.year == data["target_year"],
        )
        .first()
    )
    assert food_budget is not None
    assert food_budget.amount == Decimal(str(rec_food["recommended_amount"]))
    db.close()


def test_budget_recommendations_with_income_adaptive_50_30_20(client: TestClient):
    """Test AI budget suggestions adapt to user income via 50/30/20 and calculate true average when under 3 months."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "income_budget_user@example.com")

    cat_food = create_cat(db, user.id, "Ăn uống", CategoryType.EXPENSE)
    cat_rent = create_cat(db, user.id, "Tiền nhà trọ", CategoryType.EXPENSE)
    cat_shop = create_cat(db, user.id, "Mua sắm", CategoryType.EXPENSE)
    cat_salary = create_cat(db, user.id, "Lương", CategoryType.INCOME)

    today = date.today()
    # 1. User has 20,000,000 VND monthly income
    create_txn(db, user.id, cat_salary.id, Decimal("20000000"), CategoryType.INCOME, today)

    # 2. User has only 1 month of prior history in Mua sắm (e.g. 3,000,000 VND)
    next_month = today.month + 1 if today.month < 12 else 1
    next_year = today.year if today.month < 12 else today.year + 1
    create_txn(db, user.id, cat_shop.id, Decimal("3000000"), CategoryType.EXPENSE, today)

    with patch("app.core.ai.gemini_client.settings.GEMINI_API_KEY", ""):
        res = client.get(
            f"/api/v1/ai/budget-recommendations?target_month={next_month}&target_year={next_year}&lookback_months=3",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    data = res.json()

    rec_food = next(r for r in data["recommendations"] if r["category_id"] == cat_food.id)
    rec_rent = next(r for r in data["recommendations"] if r["category_id"] == cat_rent.id)
    rec_shop = next(r for r in data["recommendations"] if r["category_id"] == cat_shop.id)

    # Food & Rent have no history -> adapt to 20,000,000 income via 50/30/20
    # 22% of 20,000,000 = 4,400,000
    assert Decimal(str(rec_food["recommended_amount"])) >= Decimal("4400000")
    assert "50/30/20" in rec_food["reason"] or "thu nhập" in rec_food["reason"]

    # 20% of 20,000,000 = 4,000,000
    assert Decimal(str(rec_rent["recommended_amount"])) >= Decimal("4000000")
    assert "50/30/20" in rec_rent["reason"] or "thu nhập" in rec_rent["reason"]

    # Shopping had 1 month of 3,000,000 VND. Average should be 3,000,000 (divided by 1 active month, NOT divided by 3)
    assert Decimal(str(rec_shop["avg_spent"])) == Decimal("3000000.00")
    assert "1 tháng có dữ liệu" in rec_shop["reason"]

    db.close()


def test_budget_recommendations_sparse_data_uses_standard_baseline(client: TestClient):
    """Test AI budget suggestions return standard baseline (>= 5,000,000 VND) when income is small (< 2m) and transactions are sparse."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "sparse_user@example.com")

    cat_food = create_cat(db, user.id, "Ăn uống", CategoryType.EXPENSE)
    cat_rent = create_cat(db, user.id, "Nhà ở", CategoryType.EXPENSE)
    cat_trans = create_cat(db, user.id, "Đi lại", CategoryType.EXPENSE)
    cat_inc = create_cat(db, user.id, "Thu nhập phụ", CategoryType.INCOME)

    today = date.today()
    # User only has small test income 370,000 VND and 1 small expense of 10,000 VND
    create_txn(db, user.id, cat_inc.id, Decimal("370000"), CategoryType.INCOME, today)
    create_txn(db, user.id, cat_food.id, Decimal("10000"), CategoryType.EXPENSE, today)

    with patch("app.core.ai.gemini_client.settings.GEMINI_API_KEY", ""):
        res = client.get(
            "/api/v1/ai/budget-recommendations",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    data = res.json()

    # Total recommended budget must NOT collapse to 460k; must be >= 5,000,000 VND
    assert Decimal(str(data["total_recommended"])) >= Decimal("5000000")

    rec_food = next(r for r in data["recommendations"] if r["category_id"] == cat_food.id)
    rec_rent = next(r for r in data["recommendations"] if r["category_id"] == cat_rent.id)

    # Food should be standard baseline (2,500,000) not 80k
    assert Decimal(str(rec_food["recommended_amount"])) >= Decimal("2500000")
    # Rent should be standard baseline (2,000,000) not 70k
    assert Decimal(str(rec_rent["recommended_amount"])) >= Decimal("2000000")

    db.close()


# ---------------------------------------------------------------------------
# 5. FinAI Chat Message Test
# ---------------------------------------------------------------------------


def test_finai_chat_message(client: TestClient):
    """Test chatbot message with financial question."""
    db = TestingSessionLocal()
    user, token = create_user_and_auth(client, db, "chat_user@example.com")

    cat_food = create_cat(db, user.id, "Ăn uống", CategoryType.EXPENSE)
    create_txn(db, user.id, cat_food.id, Decimal("500000"), CategoryType.EXPENSE, date.today())

    # We mock Gemini to return a predictable response
    with patch("app.core.ai_chat.genai.GenerativeModel") as mock_model_cls, \
         patch("app.core.ai_chat.settings.GEMINI_API_KEY", "test-key"):
        mock_instance = mock_model_cls.return_value
        mock_response = AsyncMock()
        mock_response.text = "Tháng này bạn chi nhiều nhất vào Ăn uống với 500.000 VNĐ."
        mock_instance.generate_content_async = AsyncMock(return_value=mock_response)

        res = client.post(
            "/api/v1/chat/message",
            json={
                "message": "tháng này tôi chi nhiều nhất vào đâu?",
                "conversation_history": [],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "reply" in data
        assert len(data["reply"]) > 0

    db.close()
