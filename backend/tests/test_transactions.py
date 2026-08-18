"""Comprehensive tests for the Transaction management API.

Covers CRUD, ownership enforcement, soft-delete, restore, duplicate,
filtering, sorting, pagination and bulk import.
"""

from datetime import date
from decimal import Decimal
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
CATEGORIES_URL = "/api/v1/categories"
TRANSACTIONS_URL = "/api/v1/transactions"


def register_and_login(client, username, email, password="Test1234!"):
    """Register a user and return the auth header dict."""
    client.post(REGISTER_URL, json={
        "username": username, "email": email, "password": password,
    })
    resp = client.post(LOGIN_URL, data={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_category(client, headers, name="TestCat", icon="other", color="#D69A23", type="expense"):
    resp = client.post(CATEGORIES_URL, json={
        "name": name, "icon": icon, "color": color, "type": type,
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_transaction(client, headers, category_id, **overrides):
    payload = {
        "amount": "100.00",
        "type": "expense",
        "category_id": category_id,
        "transaction_date": "2026-07-15",
        "description": "Test ghi chú",
        "payment_method": "cash",
    }
    payload.update(overrides)
    return client.post(TRANSACTIONS_URL, json=payload, headers=headers)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def user_a(client):
    headers = register_and_login(client, "txn_user_a", "txn_a@test.com")
    cat_inc = create_category(client, headers, "Thu nhập khởi đầu A", type="income")
    client.post(
        TRANSACTIONS_URL,
        json={
            "amount": "100000000.00",
            "type": "income",
            "category_id": cat_inc["id"],
            "transaction_date": "2026-01-01",
            "description": "Khoản thu ban đầu",
        },
        headers=headers,
    )
    return headers


@pytest.fixture(scope="module")
def user_b(client):
    headers = register_and_login(client, "txn_user_b", "txn_b@test.com")
    cat_inc = create_category(client, headers, "Thu nhập khởi đầu B", type="income")
    client.post(
        TRANSACTIONS_URL,
        json={
            "amount": "100000000.00",
            "type": "income",
            "category_id": cat_inc["id"],
            "transaction_date": "2026-01-01",
            "description": "Khoản thu ban đầu",
        },
        headers=headers,
    )
    return headers


@pytest.fixture(scope="module")
def cat_expense_a(client, user_a):
    return create_category(client, user_a, "Chi phí A", type="expense")


@pytest.fixture(scope="module")
def cat_income_a(client, user_a):
    return create_category(client, user_a, "Thu nhập A", type="income")


@pytest.fixture(scope="module")
def cat_expense_b(client, user_b):
    return create_category(client, user_b, "Chi phí B", type="expense")


# ---------------------------------------------------------------------------
# 1. Create transaction – valid cases
# ---------------------------------------------------------------------------


class TestCreateTransaction:
    def test_create_valid_expense(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == "100.00"
        assert data["type"] == "expense"
        assert data["payment_method"] == "cash"
        assert data["is_deleted"] is False
        assert data["category"]["id"] == cat_expense_a["id"]

    def test_create_valid_income(self, client, user_a, cat_income_a):
        resp = create_transaction(
            client, user_a, cat_income_a["id"],
            type="income", amount="5000.50", payment_method="bank_transfer",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "income"
        assert data["amount"] == "5000.50"
        assert data["payment_method"] == "bank_transfer"

    def test_create_without_description(self, client, user_a, cat_expense_a):
        resp = create_transaction(
            client, user_a, cat_expense_a["id"], description=None,
        )
        assert resp.status_code == 201
        assert resp.json()["description"] is None

    def test_create_trims_description(self, client, user_a, cat_expense_a):
        resp = create_transaction(
            client, user_a, cat_expense_a["id"], description="  hello  ",
        )
        assert resp.status_code == 201
        assert resp.json()["description"] == "hello"

    def test_create_blank_description_becomes_null(self, client, user_a, cat_expense_a):
        resp = create_transaction(
            client, user_a, cat_expense_a["id"], description="   ",
        )
        assert resp.status_code == 201
        assert resp.json()["description"] is None


# ---------------------------------------------------------------------------
# 2. Create transaction – validation failures
# ---------------------------------------------------------------------------


class TestCreateTransactionValidation:
    def test_reject_zero_amount(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"], amount="0")
        assert resp.status_code == 422

    def test_reject_negative_amount(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"], amount="-10")
        assert resp.status_code == 422

    def test_reject_nan_amount(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"], amount="NaN")
        assert resp.status_code == 422

    def test_reject_infinity_amount(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"], amount="Infinity")
        assert resp.status_code == 422

    def test_reject_invalid_type(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"], type="savings")
        assert resp.status_code == 422

    def test_reject_invalid_payment_method(self, client, user_a, cat_expense_a):
        resp = create_transaction(
            client, user_a, cat_expense_a["id"], payment_method="crypto",
        )
        assert resp.status_code == 422

    def test_reject_other_users_category(self, client, user_a, cat_expense_b):
        resp = create_transaction(client, user_a, cat_expense_b["id"])
        assert resp.status_code == 404

    def test_reject_hidden_category(self, client, user_a):
        cat = create_category(client, user_a, "WillHide")
        client.post(f'{CATEGORIES_URL}/{cat["id"]}/hide', headers=user_a)
        resp = create_transaction(client, user_a, cat["id"])
        assert resp.status_code == 422
        assert "ẩn" in resp.json()["detail"]

    def test_reject_nonexistent_category(self, client, user_a):
        resp = create_transaction(client, user_a, 999999)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. Ownership enforcement
# ---------------------------------------------------------------------------


class TestOwnership:
    def test_cannot_view_other_users_transaction(self, client, user_a, user_b, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.get(f"{TRANSACTIONS_URL}/{txn_id}", headers=user_b)
        assert resp.status_code == 404

    def test_cannot_update_other_users_transaction(self, client, user_a, user_b, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}",
            json={"amount": "999"},
            headers=user_b,
        )
        assert resp.status_code == 404

    def test_cannot_trash_other_users_transaction(self, client, user_a, user_b, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.post(f"{TRANSACTIONS_URL}/{txn_id}/trash", headers=user_b)
        assert resp.status_code == 404

    def test_cannot_duplicate_other_users_transaction(self, client, user_a, user_b, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.post(f"{TRANSACTIONS_URL}/{txn_id}/duplicate", headers=user_b)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Update transaction
# ---------------------------------------------------------------------------


class TestUpdateTransaction:
    def test_update_amount(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}",
            json={"amount": "250.75"},
            headers=user_a,
        )
        assert resp.status_code == 200
        assert resp.json()["amount"] == "250.75"

    def test_update_description(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}",
            json={"description": "Updated note"},
            headers=user_a,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated note"

    def test_update_requires_at_least_one_field(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}", json={}, headers=user_a,
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "field",
        ["amount", "type", "category_id", "transaction_date", "payment_method"],
    )
    def test_update_rejects_explicit_null_for_required_fields(
        self, client, user_a, cat_expense_a, field
    ):
        txn = create_transaction(client, user_a, cat_expense_a["id"]).json()
        response = client.patch(
            f"{TRANSACTIONS_URL}/{txn['id']}",
            json={field: None},
            headers=user_a,
        )
        assert response.status_code == 422

    def test_update_keeps_hidden_category_if_not_changing(self, client, user_a):
        """When editing an old transaction with a hidden category, keep it
        if user doesn't change the category_id."""
        cat = create_category(client, user_a, "SoonHidden")
        resp = create_transaction(client, user_a, cat["id"])
        txn_id = resp.json()["id"]
        # Hide the category
        client.post(f'{CATEGORIES_URL}/{cat["id"]}/hide', headers=user_a)
        # Update amount without changing category
        resp = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}",
            json={"amount": "300"},
            headers=user_a,
        )
        assert resp.status_code == 200
        assert resp.json()["category_id"] == cat["id"]

    def test_update_rejects_switching_to_hidden_category(self, client, user_a):
        cat_active = create_category(client, user_a, "ActiveForSwitch")
        cat_hidden = create_category(client, user_a, "HiddenForSwitch")
        client.post(f'{CATEGORIES_URL}/{cat_hidden["id"]}/hide', headers=user_a)
        resp = create_transaction(client, user_a, cat_active["id"])
        txn_id = resp.json()["id"]
        resp = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}",
            json={"category_id": cat_hidden["id"]},
            headers=user_a,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 5. Soft-delete & trash
# ---------------------------------------------------------------------------


class TestTrash:
    def test_soft_delete(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.post(f"{TRANSACTIONS_URL}/{txn_id}/trash", headers=user_a)
        assert resp.status_code == 200
        assert resp.json()["is_deleted"] is True
        assert resp.json()["deleted_at"] is not None

    def test_trashed_not_in_default_list(self, client, user_a, cat_expense_a):
        resp = create_transaction(
            client, user_a, cat_expense_a["id"], description="willtrash",
        )
        txn_id = resp.json()["id"]
        client.post(f"{TRANSACTIONS_URL}/{txn_id}/trash", headers=user_a)
        resp = client.get(TRANSACTIONS_URL, headers=user_a)
        ids = [t["id"] for t in resp.json()["items"]]
        assert txn_id not in ids

    def test_trashed_in_trash_list(self, client, user_a, cat_expense_a):
        resp = create_transaction(
            client, user_a, cat_expense_a["id"], description="intrash",
        )
        txn_id = resp.json()["id"]
        client.post(f"{TRANSACTIONS_URL}/{txn_id}/trash", headers=user_a)
        resp = client.get(f"{TRANSACTIONS_URL}/trash", headers=user_a)
        ids = [t["id"] for t in resp.json()["items"]]
        assert txn_id in ids

    def test_restore(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        client.post(f"{TRANSACTIONS_URL}/{txn_id}/trash", headers=user_a)
        resp = client.post(f"{TRANSACTIONS_URL}/{txn_id}/restore", headers=user_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["transaction"]["is_deleted"] is False
        assert data["transaction"]["deleted_at"] is None
        assert data["category_warning"] is None

    def test_restore_with_hidden_category_warns(self, client, user_a):
        cat = create_category(client, user_a, "HideRestore")
        resp = create_transaction(client, user_a, cat["id"])
        txn_id = resp.json()["id"]
        client.post(f"{TRANSACTIONS_URL}/{txn_id}/trash", headers=user_a)
        client.post(f'{CATEGORIES_URL}/{cat["id"]}/hide', headers=user_a)
        resp = client.post(f"{TRANSACTIONS_URL}/{txn_id}/restore", headers=user_a)
        assert resp.status_code == 200
        assert resp.json()["category_warning"] is not None
        assert "ẩn" in resp.json()["category_warning"]

    def test_permanent_delete(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        client.post(f"{TRANSACTIONS_URL}/{txn_id}/trash", headers=user_a)
        resp = client.delete(f"{TRANSACTIONS_URL}/{txn_id}", headers=user_a)
        assert resp.status_code == 204
        # Should be gone
        resp = client.get(f"{TRANSACTIONS_URL}/{txn_id}", headers=user_a)
        assert resp.status_code == 404

    def test_permanent_delete_requires_trashed(self, client, user_a, cat_expense_a):
        resp = create_transaction(client, user_a, cat_expense_a["id"])
        txn_id = resp.json()["id"]
        resp = client.delete(f"{TRANSACTIONS_URL}/{txn_id}", headers=user_a)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 6. Duplicate
# ---------------------------------------------------------------------------


class TestDuplicate:
    def test_duplicate_returns_data(self, client, user_a, cat_expense_a):
        resp = create_transaction(
            client, user_a, cat_expense_a["id"], description="dup source",
        )
        txn_id = resp.json()["id"]
        resp = client.post(f"{TRANSACTIONS_URL}/{txn_id}/duplicate", headers=user_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "dup source"
        assert data["id"] == txn_id  # Returns source data, not a new record


# ---------------------------------------------------------------------------
# 7. Filtering
# ---------------------------------------------------------------------------


class TestFiltering:
    def test_filter_by_search(self, client, user_a, cat_expense_a):
        create_transaction(
            client, user_a, cat_expense_a["id"], description="cafe sáng",
        )
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a, params={"search": "cafe"},
        )
        assert resp.status_code == 200
        assert any("cafe" in (t["description"] or "") for t in resp.json()["items"])

    def test_filter_by_date_range(self, client, user_a, cat_expense_a):
        create_transaction(
            client, user_a, cat_expense_a["id"],
            transaction_date="2026-06-01", description="june txn",
        )
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a,
            params={"date_start": "2026-06-01", "date_end": "2026-06-30"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "2026-06" in item["transaction_date"]

    def test_filter_by_amount_range(self, client, user_a, cat_expense_a):
        create_transaction(
            client, user_a, cat_expense_a["id"], amount="500",
        )
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a,
            params={"amount_min": "400", "amount_max": "600"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert 400 <= float(item["amount"]) <= 600

    def test_filter_by_type(self, client, user_a, cat_expense_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a, params={"type": "expense"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["type"] == "expense"

    def test_filter_by_payment_method(self, client, user_a, cat_expense_a):
        create_transaction(
            client, user_a, cat_expense_a["id"], payment_method="bank_transfer",
        )
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a,
            params={"payment_method": "bank_transfer"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["payment_method"] == "bank_transfer"

    def test_filter_by_category(self, client, user_a, cat_expense_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a,
            params={"category_id": cat_expense_a["id"]},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["category_id"] == cat_expense_a["id"]

    def test_validate_date_range(self, client, user_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a,
            params={"date_start": "2026-12-01", "date_end": "2026-01-01"},
        )
        assert resp.status_code == 422

    def test_validate_amount_range(self, client, user_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a,
            params={"amount_min": "1000", "amount_max": "500"},
        )
        assert resp.status_code == 422

    def test_filter_category_of_other_user(self, client, user_a, cat_expense_b):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a,
            params={"category_id": cat_expense_b["id"]},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8. Sorting
# ---------------------------------------------------------------------------


class TestSorting:
    def test_sort_date_desc(self, client, user_a, cat_expense_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a, params={"sort": "date_desc"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        dates = [i["transaction_date"] for i in items]
        assert dates == sorted(dates, reverse=True)

    def test_sort_date_asc(self, client, user_a, cat_expense_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a, params={"sort": "date_asc"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        dates = [i["transaction_date"] for i in items]
        assert dates == sorted(dates)

    def test_sort_amount_desc(self, client, user_a, cat_expense_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a, params={"sort": "amount_desc"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        amounts = [float(i["amount"]) for i in items]
        assert amounts == sorted(amounts, reverse=True)

    def test_sort_amount_asc(self, client, user_a, cat_expense_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a, params={"sort": "amount_asc"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        amounts = [float(i["amount"]) for i in items]
        assert amounts == sorted(amounts)


# ---------------------------------------------------------------------------
# 9. Pagination
# ---------------------------------------------------------------------------


class TestPagination:
    def test_default_pagination(self, client, user_a, cat_expense_a):
        resp = client.get(TRANSACTIONS_URL, headers=user_a)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_custom_page_size(self, client, user_a, cat_expense_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a, params={"page_size": 2},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    def test_page_2(self, client, user_a, cat_expense_a):
        resp = client.get(
            TRANSACTIONS_URL, headers=user_a,
            params={"page": 2, "page_size": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["page"] == 2


# ---------------------------------------------------------------------------
# 10. Bulk import
# ---------------------------------------------------------------------------


class TestBulkImport:
    def test_import_valid_rows(self, client, user_a, cat_expense_a):
        resp = client.post(
            f"{TRANSACTIONS_URL}/import",
            json={
                "idempotency_key": "test-import-001",
                "rows": [
                    {
                        "amount": "100",
                        "type": "expense",
                        "category_id": cat_expense_a["id"],
                        "transaction_date": "2026-07-01",
                        "payment_method": "bank_transfer",
                    },
                    {
                        "amount": "200",
                        "type": "expense",
                        "category_id": cat_expense_a["id"],
                        "transaction_date": "2026-07-02",
                        "payment_method": "bank_transfer",
                    },
                ],
            },
            headers=user_a,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success_count"] == 2
        assert data["error_count"] == 0

    def test_import_idempotency(self, client, user_a, cat_expense_a):
        """Repeating the same import key should be rejected."""
        resp = client.post(
            f"{TRANSACTIONS_URL}/import",
            json={
                "idempotency_key": "test-import-001",
                "rows": [{
                    "amount": "50",
                    "type": "expense",
                    "category_id": cat_expense_a["id"],
                    "transaction_date": "2026-07-01",
                }],
            },
            headers=user_a,
        )
        assert resp.status_code == 409

    def test_import_rejects_other_users_category(self, client, user_a, cat_expense_b):
        resp = client.post(
            f"{TRANSACTIONS_URL}/import",
            json={
                "idempotency_key": "test-import-002",
                "rows": [{
                    "amount": "50",
                    "type": "expense",
                    "category_id": cat_expense_b["id"],
                    "transaction_date": "2026-07-01",
                }],
            },
            headers=user_a,
        )
        assert resp.status_code == 200
        assert resp.json()["error_count"] == 1

    def test_import_empty_rows_rejected(self, client, user_a):
        resp = client.post(
            f"{TRANSACTIONS_URL}/import",
            json={"idempotency_key": "test-import-003", "rows": []},
            headers=user_a,
        )
        assert resp.status_code == 422

    def test_import_partial_success_preserves_valid_rows_across_errors(
        self, client, user_a, cat_expense_a, cat_expense_b
    ):
        """Row 0 is valid, Row 1 is invalid category (other user's), Row 2 is valid.
        Both Row 0 and Row 2 must be committed into DB without Row 0 being lost.
        """
        resp = client.post(
            f"{TRANSACTIONS_URL}/import",
            json={
                "idempotency_key": "test-import-partial-001",
                "rows": [
                    {
                        "amount": "100.00",
                        "type": "expense",
                        "category_id": cat_expense_a["id"],
                        "transaction_date": "2026-08-01",
                        "description": "Row 0 valid",
                    },
                    {
                        "amount": "200.00",
                        "type": "expense",
                        "category_id": cat_expense_b["id"],
                        "transaction_date": "2026-08-02",
                        "description": "Row 1 invalid",
                    },
                    {
                        "amount": "300.00",
                        "type": "expense",
                        "category_id": cat_expense_a["id"],
                        "transaction_date": "2026-08-03",
                        "description": "Row 2 valid",
                    },
                ],
            },
            headers=user_a,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success_count"] == 2
        assert data["error_count"] == 1
        assert data["results"][0]["status"] == "success"
        assert data["results"][1]["status"] == "error"
        assert data["results"][2]["status"] == "success"

        # Verify Row 0 and Row 2 are both in the DB
        list_resp = client.get(TRANSACTIONS_URL, headers=user_a)
        items = list_resp.json()["items"]
        descriptions = [i["description"] for i in items]
        assert "Row 0 valid" in descriptions
        assert "Row 2 valid" in descriptions
        assert "Row 1 invalid" not in descriptions


class TestTransactionSummary:
    def test_summary_returns_accurate_balances(self, client):
        summary_user = register_and_login(client, "summary_tester", "summary_tester@test.com")
        cat_inc = create_category(client, summary_user, "Thu nhập test", icon="salary", type="income")
        cat_exp = create_category(client, summary_user, "Chi tiêu test", icon="food", type="expense")

        # Add income: 2000.00, expense: 200.00 (plus trashed 999.00)
        client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "2000.00",
                "type": "income",
                "category_id": cat_inc["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=summary_user,
        )
        del_txn = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "999.00",
                "type": "expense",
                "category_id": cat_exp["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=summary_user,
        ).json()
        # Soft delete this 999.00 expense
        client.post(f"{TRANSACTIONS_URL}/{del_txn['id']}/trash", headers=summary_user)

        client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "200.00",
                "type": "expense",
                "category_id": cat_exp["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=summary_user,
        )

        resp = client.get(f"{TRANSACTIONS_URL}/summary", headers=summary_user)
        assert resp.status_code == 200
        data = resp.json()
        assert data["all_time_income"] == "2000.00"
        assert data["all_time_expense"] == "200.00"
        assert data["total_balance"] == "1800.00"
        assert data["available_balance"] == "1800.00"
        assert data["saving_balance"] == "0.00"
        assert data["month_income"] == "2000.00"
        assert data["month_expense"] == "200.00"
        assert data["month_net"] == "1800.00"

        # Now create a saving goal with deposit 100.00
        client.post(
            "/api/v1/saving-goals",
            json={"name": "Heo đất", "target_amount": "1000.00", "initial_deposit": "100.00"},
            headers=summary_user,
        )
        resp2 = client.get(f"{TRANSACTIONS_URL}/summary", headers=summary_user)
        data2 = resp2.json()
        assert data2["total_balance"] == "1800.00"
        assert data2["saving_balance"] == "100.00"
        assert data2["available_balance"] == "1700.00"



class TestCategoryValidationConstraints:
    """Test validation of category constraints (type matching, soft-delete exclusion)."""

    def test_cannot_create_transaction_with_mismatched_category_type(
        self, client, user_a, cat_expense_a
    ):
        # Attempt to create an 'income' transaction with an 'expense' category
        res = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "100.00",
                "type": "income",
                "category_id": cat_expense_a["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user_a,
        )
        assert res.status_code == 422
        assert "không khớp" in res.json()["detail"]

    def test_cannot_create_transaction_with_soft_deleted_category(
        self, client, user_a
    ):
        cat = create_category(client, user_a, "Tam thoi xoa", icon="other", type="expense")
        cat_id = cat["id"]

        # Soft delete the category
        del_res = client.delete(f"/api/v1/categories/{cat_id}", headers=user_a)
        assert del_res.status_code == 204

        # Attempt to create transaction with soft-deleted category
        res = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "50.00",
                "type": "expense",
                "category_id": cat_id,
                "transaction_date": date.today().isoformat(),
            },
            headers=user_a,
        )
        assert res.status_code == 404
        assert "Không tìm thấy danh mục" in res.json()["detail"]

    def test_create_income_transaction_with_saving_allocation(
        self, client, user_a, cat_income_a
    ):
        # 1. Create a saving goal
        goal_resp = client.post(
            "/api/v1/saving-goals",
            json={"name": "Quỹ mua xe SH", "target_amount": "50000000.00"},
            headers=user_a,
        )
        assert goal_resp.status_code == 201
        goal_id = goal_resp.json()["id"]

        # 2. Create income transaction with allocation
        txn_resp = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "10000000.00",
                "type": "income",
                "category_id": cat_income_a["id"],
                "transaction_date": date.today().isoformat(),
                "description": "Thưởng doanh số quý 3",
                "saving_goal_id": goal_id,
                "saving_goal_amount": "2000000.00",
            },
            headers=user_a,
        )
        assert txn_resp.status_code == 201
        txn_id = txn_resp.json()["id"]

        # 3. Verify saving goal updated
        goal_updated = client.get(f"/api/v1/saving-goals/{goal_id}", headers=user_a).json()
        assert Decimal(goal_updated["current_amount"]) == Decimal("2000000.00")
        assert len(goal_updated["contributions"]) == 1
        assert goal_updated["contributions"][0]["source"] == "income_allocation"
        assert goal_updated["contributions"][0]["transaction_id"] == txn_id
        assert Decimal(goal_updated["contributions"][0]["amount"]) == Decimal("2000000.00")

    def test_create_transaction_rejects_saving_allocation_on_expense(
        self, client, user_a, cat_expense_a
    ):
        goal = client.post(
            "/api/v1/saving-goals",
            json={"name": "Goal test expense", "target_amount": "10000000.00"},
            headers=user_a,
        ).json()

        res = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "500000.00",
                "type": "expense",
                "category_id": cat_expense_a["id"],
                "transaction_date": date.today().isoformat(),
                "saving_goal_id": goal["id"],
                "saving_goal_amount": "100000.00",
            },
            headers=user_a,
        )
        assert res.status_code == 422
        assert "Chỉ có thể trích tiền vào mục tiêu tiết kiệm đối với giao dịch thu nhập" in res.text

    def test_trash_and_restore_income_with_saving_allocation(
        self, client, user_a, cat_income_a
    ):
        # 1. Create goal
        goal = client.post(
            "/api/v1/saving-goals",
            json={"name": "Mục tiêu mua laptop", "target_amount": "5000000.00"},
            headers=user_a,
        ).json()
        goal_id = goal["id"]

        # 2. Create income transaction with 5,000,000 allocating 5,000,000 to goal -> auto completes
        txn = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "5000000.00",
                "type": "income",
                "category_id": cat_income_a["id"],
                "transaction_date": date.today().isoformat(),
                "description": "Lương tháng này",
                "saving_goal_id": goal_id,
                "saving_goal_amount": "5000000.00",
            },
            headers=user_a,
        ).json()
        txn_id = txn["id"]

        # Goal is now completed
        goal_status = client.get(f"/api/v1/saving-goals/{goal_id}", headers=user_a).json()
        assert goal_status["status"] == "completed"
        assert Decimal(goal_status["current_amount"]) == Decimal("5000000.00")

        # 3. Trash the transaction -> goal current_amount should reduce and status revert to active
        trash_resp = client.post(f"{TRANSACTIONS_URL}/{txn_id}/trash", headers=user_a)
        assert trash_resp.status_code == 200

        goal_after_trash = client.get(f"/api/v1/saving-goals/{goal_id}", headers=user_a).json()
        assert Decimal(goal_after_trash["current_amount"]) == Decimal("0.00")
        assert goal_after_trash["status"] == "active"

        # 4. Restore the transaction -> goal current_amount should restore to 5,000,000 and status completed
        restore_resp = client.post(f"{TRANSACTIONS_URL}/{txn_id}/restore", headers=user_a)
        assert restore_resp.status_code == 200

        goal_after_restore = client.get(f"/api/v1/saving-goals/{goal_id}", headers=user_a).json()
        assert Decimal(goal_after_restore["current_amount"]) == Decimal("5000000.00")
        assert goal_after_restore["status"] == "completed"

    def test_restore_income_allocation_keeps_cancelled_goal_consistent(self, client):
        user = register_and_login(
            client,
            "restore_cancelled_goal_user",
            "restore_cancelled_goal@example.com",
        )
        income_category = create_category(
            client,
            user,
            "Thu nhập cho mục tiêu đã hủy",
            type="income",
        )
        goal = client.post(
            "/api/v1/saving-goals",
            json={"name": "Quỹ dự phòng", "target_amount": "200000.00"},
            headers=user,
        ).json()
        transaction = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "100000.00",
                "type": "income",
                "category_id": income_category["id"],
                "transaction_date": date.today().isoformat(),
                "saving_goal_id": goal["id"],
                "saving_goal_amount": "30000.00",
            },
            headers=user,
        ).json()

        assert client.patch(
            f"/api/v1/saving-goals/{goal['id']}",
            json={"status": "cancelled"},
            headers=user,
        ).status_code == 200
        assert client.post(
            f"{TRANSACTIONS_URL}/{transaction['id']}/trash",
            headers=user,
        ).status_code == 200

        after_trash = client.get(
            f"/api/v1/saving-goals/{goal['id']}", headers=user
        ).json()
        assert after_trash["status"] == "cancelled"
        assert Decimal(after_trash["current_amount"]) == Decimal("0.00")

        restore_response = client.post(
            f"{TRANSACTIONS_URL}/{transaction['id']}/restore",
            headers=user,
        )
        assert restore_response.status_code == 200

        after_restore = client.get(
            f"/api/v1/saving-goals/{goal['id']}", headers=user
        ).json()
        assert after_restore["status"] == "cancelled"
        assert Decimal(after_restore["current_amount"]) == Decimal("30000.00")
        assert len(after_restore["contributions"]) == 1
        assert Decimal(after_restore["contributions"][0]["amount"]) == Decimal("30000.00")

        cancelled_summary = client.get(
            f"{TRANSACTIONS_URL}/summary", headers=user
        ).json()
        assert Decimal(cancelled_summary["available_balance"]) == Decimal("100000.00")
        assert Decimal(cancelled_summary["saving_balance"]) == Decimal("0.00")

        reactivate_response = client.patch(
            f"/api/v1/saving-goals/{goal['id']}",
            json={"status": "active"},
            headers=user,
        )
        assert reactivate_response.status_code == 200
        assert Decimal(reactivate_response.json()["current_amount"]) == Decimal("30000.00")

        active_summary = client.get(
            f"{TRANSACTIONS_URL}/summary", headers=user
        ).json()
        assert Decimal(active_summary["saving_balance"]) == Decimal("30000.00")
        assert Decimal(active_summary["available_balance"]) == Decimal("70000.00")

    def test_update_income_with_saving_allocation_validations(
        self, client, user_a, cat_income_a, cat_expense_a
    ):
        goal = client.post(
            "/api/v1/saving-goals",
            json={"name": "Mục tiêu mua điện thoại", "target_amount": "10000000.00"},
            headers=user_a,
        ).json()
        goal_id = goal["id"]

        txn = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "6000000.00",
                "type": "income",
                "category_id": cat_income_a["id"],
                "transaction_date": date.today().isoformat(),
                "saving_goal_id": goal_id,
                "saving_goal_amount": "3000000.00",
            },
            headers=user_a,
        ).json()
        txn_id = txn["id"]

        # Attempt to change type to expense -> rejected
        resp_type_fail = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}",
            json={"type": "expense", "category_id": cat_expense_a["id"]},
            headers=user_a,
        )
        assert resp_type_fail.status_code == 400
        assert "không thể đổi loại thành chi tiêu" in resp_type_fail.json()["detail"]

        # Attempt to reduce amount below allocated 3,000,000 -> rejected
        resp_amount_fail = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}",
            json={"amount": "2000000.00"},
            headers=user_a,
        )
        assert resp_amount_fail.status_code == 400
        assert "không thể nhỏ hơn tổng số tiền đã trích" in resp_amount_fail.json()["detail"]

        # Update amount to 4,000,000 (>= 3,000,000) -> success
        resp_amount_ok = client.patch(
            f"{TRANSACTIONS_URL}/{txn_id}",
            json={"amount": "4000000.00"},
            headers=user_a,
        )
        assert resp_amount_ok.status_code == 200
        assert Decimal(resp_amount_ok.json()["amount"]) == Decimal("4000000.00")


class TestAvailableBalanceEnforcement:
    """Test strict balance enforcement when creating/updating/restoring expense transactions."""

    def test_cannot_create_expense_with_zero_balance(self, client):
        user = register_and_login(client, "broke_user", "broke@test.com")
        cat_exp = create_category(client, user, "Chi test 0 balance", type="expense")
        resp = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "50000.00",
                "type": "expense",
                "category_id": cat_exp["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user,
        )
        assert resp.status_code == 400
        assert "vượt quá số dư khả dụng hiện có" in resp.json()["detail"]

    def test_cannot_create_expense_exceeding_available_balance(self, client):
        user = register_and_login(client, "limited_user", "limited@test.com")
        cat_inc = create_category(client, user, "Thu test limit", type="income")
        cat_exp = create_category(client, user, "Chi test limit", type="expense")
        # Add income 100k
        client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "100000.00",
                "type": "income",
                "category_id": cat_inc["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user,
        )
        # Try expense 150k -> 400
        resp = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "150000.00",
                "type": "expense",
                "category_id": cat_exp["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user,
        )
        assert resp.status_code == 400
        assert "vượt quá số dư khả dụng hiện có" in resp.json()["detail"]

        # Expense 80k -> 201 (remaining 20k)
        resp_ok = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "80000.00",
                "type": "expense",
                "category_id": cat_exp["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user,
        )
        assert resp_ok.status_code == 201

        # Try another 30k -> 400 (only 20k left)
        resp_fail = client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "30000.00",
                "type": "expense",
                "category_id": cat_exp["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user,
        )
        assert resp_fail.status_code == 400

    def test_cannot_update_expense_exceeding_available_balance(self, client):
        user = register_and_login(client, "update_user", "update@test.com")
        cat_inc = create_category(client, user, "Thu test update", type="income")
        cat_exp = create_category(client, user, "Chi test update", type="expense")
        # Income 100k
        client.post(
            TRANSACTIONS_URL,
            json={"amount": "100000.00", "type": "income", "category_id": cat_inc["id"], "transaction_date": date.today().isoformat()},
            headers=user,
        )
        # Expense 50k -> remaining 50k
        txn = client.post(
            TRANSACTIONS_URL,
            json={"amount": "50000.00", "type": "expense", "category_id": cat_exp["id"], "transaction_date": date.today().isoformat()},
            headers=user,
        ).json()

        # Update expense from 50k to 120k (+70k > 50k avail) -> 400
        resp_fail = client.patch(
            f"{TRANSACTIONS_URL}/{txn['id']}",
            json={"amount": "120000.00"},
            headers=user,
        )
        assert resp_fail.status_code == 400
        assert "tăng thêm" in resp_fail.json()["detail"]

        # Update expense to 90k (+40k <= 50k avail) -> 200
        resp_ok = client.patch(
            f"{TRANSACTIONS_URL}/{txn['id']}",
            json={"amount": "90000.00"},
            headers=user,
        )
        assert resp_ok.status_code == 200

    def test_cannot_restore_expense_exceeding_available_balance(self, client):
        user = register_and_login(client, "restore_user", "restore@test.com")
        cat_inc = create_category(client, user, "Thu test restore", type="income")
        cat_exp = create_category(client, user, "Chi test restore", type="expense")
        # Income 100k
        client.post(
            TRANSACTIONS_URL,
            json={"amount": "100000.00", "type": "income", "category_id": cat_inc["id"], "transaction_date": date.today().isoformat()},
            headers=user,
        )
        # Expense 60k
        txn = client.post(
            TRANSACTIONS_URL,
            json={"amount": "60000.00", "type": "expense", "category_id": cat_exp["id"], "transaction_date": date.today().isoformat()},
            headers=user,
        ).json()
        # Soft delete 60k -> available balance restores to 100k
        client.post(f"{TRANSACTIONS_URL}/{txn['id']}/trash", headers=user)

        # Spend 80k on other expense -> available balance drops to 20k
        client.post(
            TRANSACTIONS_URL,
            json={"amount": "80000.00", "type": "expense", "category_id": cat_exp["id"], "transaction_date": date.today().isoformat()},
            headers=user,
        )

        # Try to restore 60k expense -> fails (20k < 60k)
        resp_restore_fail = client.post(f"{TRANSACTIONS_URL}/{txn['id']}/restore", headers=user)
        assert resp_restore_fail.status_code == 400
        assert "Khôi phục giao dịch chi tiêu" in resp_restore_fail.json()["detail"]

    def test_cannot_reduce_income_when_projected_balance_is_negative(self, client):
        user = register_and_login(client, "reduce_income_user", "reduce_income@test.com")
        cat_inc = create_category(client, user, "Thu để giảm", type="income")
        cat_exp = create_category(client, user, "Chi sau thu", type="expense")
        income = create_transaction(
            client,
            user,
            cat_inc["id"],
            type="income",
            amount="100000.00",
        ).json()
        assert create_transaction(
            client, user, cat_exp["id"], amount="80000.00"
        ).status_code == 201

        response = client.patch(
            f"{TRANSACTIONS_URL}/{income['id']}",
            json={"amount": "10000.00"},
            headers=user,
        )
        assert response.status_code == 400
        assert "số dư khả dụng bị âm" in response.json()["detail"]

        unchanged = client.get(
            f"{TRANSACTIONS_URL}/{income['id']}", headers=user
        )
        assert unchanged.json()["amount"] == "100000.00"

    def test_cannot_trash_income_when_projected_balance_is_negative(self, client):
        user = register_and_login(client, "trash_income_user", "trash_income@test.com")
        cat_inc = create_category(client, user, "Thu để xóa", type="income")
        cat_exp = create_category(client, user, "Chi trước xóa", type="expense")
        income = create_transaction(
            client,
            user,
            cat_inc["id"],
            type="income",
            amount="100000.00",
        ).json()
        assert create_transaction(
            client, user, cat_exp["id"], amount="80000.00"
        ).status_code == 201

        response = client.post(
            f"{TRANSACTIONS_URL}/{income['id']}/trash", headers=user
        )
        assert response.status_code == 400
        assert "Không thể xóa nguồn thu" in response.json()["detail"]

        still_active = client.get(
            f"{TRANSACTIONS_URL}/{income['id']}", headers=user
        )
        assert still_active.status_code == 200
