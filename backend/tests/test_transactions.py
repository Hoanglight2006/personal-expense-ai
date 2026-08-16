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
    return register_and_login(client, "txn_user_a", "txn_a@test.com")


@pytest.fixture(scope="module")
def user_b(client):
    return register_and_login(client, "txn_user_b", "txn_b@test.com")


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

        # Add income: 500.00, expense: 200.00
        client.post(
            TRANSACTIONS_URL,
            json={
                "amount": "500.00",
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
        assert data["all_time_income"] == "500.00"
        assert data["all_time_expense"] == "200.00"
        assert data["available_balance"] == "300.00"
        assert data["month_income"] == "500.00"
        assert data["month_expense"] == "200.00"
        assert data["month_net"] == "300.00"



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

    def test_import_transactions_rejects_mismatched_or_deleted_category(
        self, client, user_a, cat_expense_a
    ):
        # 1. Row with mismatched type
        payload = {
            "idempotency_key": "test-import-val-1",
            "rows": [
                {
                    "amount": "200.00",
                    "type": "income",  # Mismatch with expense category
                    "category_id": cat_expense_a["id"],
                    "transaction_date": "2026-08-01",
                    "description": "Income mismatch",
                }
            ],
        }
        res = client.post(f"{TRANSACTIONS_URL}/import", json=payload, headers=user_a)
        assert res.status_code == 200
        data = res.json()
        assert data["success_count"] == 0
        assert data["error_count"] == 1
        assert "không khớp" in data["results"][0]["error"]



