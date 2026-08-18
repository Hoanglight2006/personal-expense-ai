"""Comprehensive tests for the Budget management and alert API routes.

Covers CRUD, ownership enforcement, duplicate checks, income category rejection,
real-time spending calculations (normal/warning/exceeded), and alert queries.
"""

from decimal import Decimal
import pytest

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
CATEGORIES_URL = "/api/v1/categories"
TRANSACTIONS_URL = "/api/v1/transactions"
BUDGETS_URL = "/api/v1/budgets"


def register_and_login(client, username, email, password="Test1234!"):
    """Register a user and return the auth header dict."""
    client.post(
        REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    resp = client.post(LOGIN_URL, data={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_category(client, headers, name="Ăn uống", icon="food", color="#C87941", type="expense"):
    resp = client.post(
        CATEGORIES_URL,
        json={"name": name, "icon": icon, "color": color, "type": type},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_transaction(client, headers, category_id, amount, txn_date, txn_type="expense"):
    resp = client.post(
        TRANSACTIONS_URL,
        json={
            "amount": amount,
            "type": txn_type,
            "category_id": category_id,
            "transaction_date": txn_date,
            "payment_method": "cash",
            "description": "Chi tiêu test",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture(scope="module")
def user_a(client):
    headers = register_and_login(client, "budget_user_a", "budget_a@test.com")
    cat_inc = create_category(client, headers, "Thu nhập ngân sách A", type="income")
    client.post(
        TRANSACTIONS_URL,
        json={
            "amount": "100000000.00",
            "type": "income",
            "category_id": cat_inc["id"],
            "transaction_date": "2026-01-01",
            "description": "Khoản thu ngân sách",
        },
        headers=headers,
    )
    return headers


@pytest.fixture(scope="module")
def user_b(client):
    return register_and_login(client, "budget_user_b", "budget_b@test.com")


class TestBudgetCreation:
    """Tests for creating monthly category budgets."""

    def test_create_budget_success(self, client, user_a):
        cat = create_category(client, user_a, name="Ăn uống T8", type="expense")
        payload = {
            "category_id": cat["id"],
            "amount": "1000000.00",
            "month": 8,
            "year": 2026,
        }
        resp = client.post(BUDGETS_URL, json=payload, headers=user_a)
        assert resp.status_code == 201
        data = resp.json()
        assert data["category_id"] == cat["id"]
        assert Decimal(str(data["amount"])) == Decimal("1000000.00")
        assert data["month"] == 8
        assert data["year"] == 2026
        assert Decimal(str(data["spent_amount"])) == Decimal("0.00")
        assert Decimal(str(data["remaining_amount"])) == Decimal("1000000.00")
        assert data["percentage_used"] == 0.0
        assert data["status"] == "normal"
        assert data["category"]["name"] == "Ăn uống T8"

    def test_create_budget_rejects_income_category(self, client, user_a):
        income_cat = create_category(client, user_a, name="Lương T8", type="income")
        payload = {
            "category_id": income_cat["id"],
            "amount": "5000000.00",
            "month": 8,
            "year": 2026,
        }
        resp = client.post(BUDGETS_URL, json=payload, headers=user_a)
        # Requirements explicitly require HTTP 422 for income category budget attempt
        assert resp.status_code == 422
        assert "Chi tiêu" in resp.json()["detail"]

    def test_create_budget_duplicate_month_conflict(self, client, user_a):
        cat = create_category(client, user_a, name="Di chuyển T8", type="expense")
        payload = {
            "category_id": cat["id"],
            "amount": "500000.00",
            "month": 8,
            "year": 2026,
        }
        resp1 = client.post(BUDGETS_URL, json=payload, headers=user_a)
        assert resp1.status_code == 201

        resp2 = client.post(BUDGETS_URL, json=payload, headers=user_a)
        assert resp2.status_code == 409
        assert "Đã thiết lập ngân sách" in resp2.json()["detail"]

    def test_create_budget_invalid_amount_or_period(self, client, user_a):
        cat = create_category(client, user_a, name="Giải trí T8", type="expense")
        # amount <= 0
        resp = client.post(
            BUDGETS_URL,
            json={"category_id": cat["id"], "amount": "0.00", "month": 8, "year": 2026},
            headers=user_a,
        )
        assert resp.status_code == 422

        # month > 12
        resp = client.post(
            BUDGETS_URL,
            json={"category_id": cat["id"], "amount": "100000.00", "month": 13, "year": 2026},
            headers=user_a,
        )
        assert resp.status_code == 422

    def test_create_budget_other_user_category(self, client, user_a, user_b):
        cat_b = create_category(client, user_b, name="Mua sắm User B", type="expense")
        payload = {
            "category_id": cat_b["id"],
            "amount": "1000000.00",
            "month": 8,
            "year": 2026,
        }
        resp = client.post(BUDGETS_URL, json=payload, headers=user_a)
        assert resp.status_code == 404


class TestBudgetCalculationAndAlerts:
    """Tests for real-time spending calculations and alert thresholds."""

    def test_spending_statuses_normal_warning_exceeded(self, client, user_a):
        # 1. Category 1: Normal (< 80%) -> 40% spent
        cat_normal = create_category(client, user_a, name="Điện nước T8", type="expense")
        client.post(
            BUDGETS_URL,
            json={"category_id": cat_normal["id"], "amount": "1000000.00", "month": 8, "year": 2026},
            headers=user_a,
        )
        create_transaction(client, user_a, cat_normal["id"], "400000.00", "2026-08-05")

        # 2. Category 2: Warning (80% - 99.9%) -> 85% spent
        cat_warning = create_category(client, user_a, name="Xăng xe T8", type="expense")
        client.post(
            BUDGETS_URL,
            json={"category_id": cat_warning["id"], "amount": "1000000.00", "month": 8, "year": 2026},
            headers=user_a,
        )
        create_transaction(client, user_a, cat_warning["id"], "850000.00", "2026-08-10")

        # 3. Category 3: Exceeded (>= 100%) -> 110% spent
        cat_exceeded = create_category(client, user_a, name="Mua sắm T8", type="expense")
        client.post(
            BUDGETS_URL,
            json={"category_id": cat_exceeded["id"], "amount": "1000000.00", "month": 8, "year": 2026},
            headers=user_a,
        )
        create_transaction(client, user_a, cat_exceeded["id"], "1100000.00", "2026-08-12")

        # Query GET /budgets?month=8&year=2026
        resp = client.get(f"{BUDGETS_URL}?month=8&year=2026", headers=user_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["month"] == 8
        assert data["year"] == 2026

        item_map = {item["category_id"]: item for item in data["items"]}

        # Check normal
        assert item_map[cat_normal["id"]]["status"] == "normal"
        assert item_map[cat_normal["id"]]["percentage_used"] == 40.0
        assert Decimal(str(item_map[cat_normal["id"]]["spent_amount"])) == Decimal("400000.00")
        assert Decimal(str(item_map[cat_normal["id"]]["remaining_amount"])) == Decimal("600000.00")

        # Check warning
        assert item_map[cat_warning["id"]]["status"] == "warning"
        assert item_map[cat_warning["id"]]["percentage_used"] == 85.0
        assert Decimal(str(item_map[cat_warning["id"]]["spent_amount"])) == Decimal("850000.00")
        assert Decimal(str(item_map[cat_warning["id"]]["remaining_amount"])) == Decimal("150000.00")

        # Check exceeded
        assert item_map[cat_exceeded["id"]]["status"] == "exceeded"
        assert item_map[cat_exceeded["id"]]["percentage_used"] == 110.0
        assert Decimal(str(item_map[cat_exceeded["id"]]["spent_amount"])) == Decimal("1100000.00")
        assert Decimal(str(item_map[cat_exceeded["id"]]["remaining_amount"])) == Decimal("-100000.00")

        # Query GET /budgets/alerts?month=8&year=2026
        alert_resp = client.get(f"{BUDGETS_URL}/alerts?month=8&year=2026", headers=user_a)
        assert alert_resp.status_code == 200
        alerts = alert_resp.json()
        assert alerts["count"] >= 2
        alert_cat_ids = [a["category_id"] for a in alerts["items"]]
        assert cat_exceeded["id"] in alert_cat_ids
        assert cat_warning["id"] in alert_cat_ids
        assert cat_normal["id"] not in alert_cat_ids
        # Sorted descending by percentage_used
        assert alerts["items"][0]["percentage_used"] >= alerts["items"][1]["percentage_used"]


class TestBudgetUpdateAndDelete:
    """Tests for modifying and deleting budgets."""

    def test_update_budget_amount(self, client, user_a):
        cat = create_category(client, user_a, name="Học tập T8", type="expense")
        create_resp = client.post(
            BUDGETS_URL,
            json={"category_id": cat["id"], "amount": "1000000.00", "month": 8, "year": 2026},
            headers=user_a,
        )
        budget_id = create_resp.json()["id"]

        create_transaction(client, user_a, cat["id"], "900000.00", "2026-08-15")

        # Initially warning at 90%
        get_resp = client.get(f"{BUDGETS_URL}/{budget_id}", headers=user_a)
        assert get_resp.json()["status"] == "warning"

        # Update budget limit up to 2,000,000 -> status changes to normal (45%)
        patch_resp = client.patch(
            f"{BUDGETS_URL}/{budget_id}",
            json={"amount": "2000000.00"},
            headers=user_a,
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert Decimal(str(data["amount"])) == Decimal("2000000.00")
        assert data["percentage_used"] == 45.0
        assert data["status"] == "normal"

    def test_delete_budget(self, client, user_a):
        cat = create_category(client, user_a, name="Bảo hiểm T8", type="expense")
        create_resp = client.post(
            BUDGETS_URL,
            json={"category_id": cat["id"], "amount": "500000.00", "month": 8, "year": 2026},
            headers=user_a,
        )
        budget_id = create_resp.json()["id"]

        del_resp = client.delete(f"{BUDGETS_URL}/{budget_id}", headers=user_a)
        assert del_resp.status_code == 200

        get_resp = client.get(f"{BUDGETS_URL}/{budget_id}", headers=user_a)
        assert get_resp.status_code == 404

    def test_user_isolation_for_patch_and_delete(self, client, user_a, user_b):
        cat_a = create_category(client, user_a, name="Gym T8", type="expense")
        create_resp = client.post(
            BUDGETS_URL,
            json={"category_id": cat_a["id"], "amount": "500000.00", "month": 8, "year": 2026},
            headers=user_a,
        )
        budget_id = create_resp.json()["id"]

        # User B cannot view, patch or delete User A's budget
        assert client.get(f"{BUDGETS_URL}/{budget_id}", headers=user_b).status_code == 404
        assert (
            client.patch(
                f"{BUDGETS_URL}/{budget_id}",
                json={"amount": "600000.00"},
                headers=user_b,
            ).status_code
            == 404
        )
        assert client.delete(f"{BUDGETS_URL}/{budget_id}", headers=user_b).status_code == 404
