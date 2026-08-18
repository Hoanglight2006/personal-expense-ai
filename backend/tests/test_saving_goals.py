"""Comprehensive tests for the Saving Goals API routes.

Covers:
- Goal creation (with & without initial deposit)
- Target amount and deadline validation
- Summary metrics and status filtering
- Goal details and contribution history
- Deposit flow (atomic contribution, current_amount update, auto-completion at 100%)
- Goal updating and deletion
- Ownership and IDOR protection
- Authentication checks
"""

from datetime import date, timedelta
from decimal import Decimal
import pytest

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
GOALS_URL = "/api/v1/saving-goals"


def register_and_login(client, username, email, password="TestPassword123!", add_income=True):
    """Register a user, optionally add initial income for available balance, and return the auth header."""
    client.post(
        REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    resp = client.post(LOGIN_URL, data={"username": username, "password": password})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    if add_income:
        # Create an income category and add a large income transaction
        cat_resp = client.post(
            "/api/v1/categories",
            json={"name": f"Lương {username}", "type": "income", "icon": "other", "color": "#10B981"},
            headers=headers,
        )
        if cat_resp.status_code == 201:
            cat_id = cat_resp.json()["id"]
            client.post(
                "/api/v1/transactions",
                json={
                    "amount": "500000000.00",
                    "type": "income",
                    "category_id": cat_id,
                    "transaction_date": date.today().isoformat(),
                    "description": "Lương tháng khởi tạo",
                },
                headers=headers,
            )

    return headers


@pytest.fixture(scope="module")
def user_a(client):
    return register_and_login(client, "saving_user_a", "saving_a@example.com")


@pytest.fixture(scope="module")
def user_b(client):
    return register_and_login(client, "saving_user_b", "saving_b@example.com")


class TestSavingGoalsCRUD:
    """Test CRUD operations for saving goals."""

    def test_create_saving_goal_success(self, client, user_a):
        future_date = (date.today() + timedelta(days=90)).isoformat()
        payload = {
            "name": "Mua laptop mới",
            "target_amount": "25000000.00",
            "deadline": future_date,
        }
        resp = client.post(GOALS_URL, json=payload, headers=user_a)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Mua laptop mới"
        assert Decimal(data["target_amount"]) == Decimal("25000000.00")
        assert Decimal(data["current_amount"]) == Decimal("0.00")
        assert data["status"] == "active"
        assert data["progress_percentage"] == 0.0
        assert Decimal(data["remaining_amount"]) == Decimal("25000000.00")
        assert data["days_remaining"] == 90
        assert data["contributions"] == []

    def test_create_saving_goal_with_initial_deposit(self, client, user_a):
        payload = {
            "name": "Quỹ du lịch Đà Nẵng",
            "target_amount": "10000000.00",
            "initial_deposit": "2000000.00",
            "deadline": (date.today() + timedelta(days=60)).isoformat(),
        }
        resp = client.post(GOALS_URL, json=payload, headers=user_a)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Quỹ du lịch Đà Nẵng"
        assert Decimal(data["current_amount"]) == Decimal("2000000.00")
        assert data["progress_percentage"] == 20.0
        assert Decimal(data["remaining_amount"]) == Decimal("8000000.00")
        assert len(data["contributions"]) == 1
        assert Decimal(data["contributions"][0]["amount"]) == Decimal("2000000.00")
        assert data["contributions"][0]["source"] == "manual"
        assert data["contributions"][0]["note"] == "Khoản nạp ban đầu"

    def test_create_saving_goal_with_full_initial_deposit_auto_completes(self, client, user_a):
        payload = {
            "name": "Khóa học React",
            "target_amount": "3000000.00",
            "initial_deposit": "3000000.00",
        }
        resp = client.post(GOALS_URL, json=payload, headers=user_a)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "completed"
        assert data["progress_percentage"] == 100.0

    def test_create_goal_validations(self, client, user_a):
        # Target amount <= 0
        resp = client.post(
            GOALS_URL,
            json={"name": "Test", "target_amount": "-1000"},
            headers=user_a,
        )
        assert resp.status_code == 422

        # Past deadline
        past_date = (date.today() - timedelta(days=5)).isoformat()
        resp = client.post(
            GOALS_URL,
            json={"name": "Test", "target_amount": "5000000", "deadline": past_date},
            headers=user_a,
        )
        assert resp.status_code == 422

        # Empty name
        resp = client.post(
            GOALS_URL,
            json={"name": "", "target_amount": "5000000"},
            headers=user_a,
        )
        assert resp.status_code == 422

    def test_list_saving_goals_and_metrics(self, client, user_a):
        resp = client.get(GOALS_URL, headers=user_a)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_target_amount" in data
        assert "total_current_amount" in data
        assert "total_goals_count" in data
        assert "active_goals_count" in data
        assert "completed_goals_count" in data
        assert len(data["items"]) >= 3

        # Test filtering by status
        resp_active = client.get(f"{GOALS_URL}?status=active", headers=user_a)
        assert resp_active.status_code == 200
        active_items = resp_active.json()["items"]
        assert all(item["status"] == "active" for item in active_items)

        resp_completed = client.get(f"{GOALS_URL}?status=completed", headers=user_a)
        assert resp_completed.status_code == 200
        completed_items = resp_completed.json()["items"]
        assert all(item["status"] == "completed" for item in completed_items)

    def test_get_saving_goal_detail(self, client, user_a):
        # Create a goal
        created = client.post(
            GOALS_URL,
            json={"name": "Quỹ dự phòng", "target_amount": "50000000.00"},
            headers=user_a,
        ).json()
        goal_id = created["id"]

        resp = client.get(f"{GOALS_URL}/{goal_id}", headers=user_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == goal_id
        assert data["name"] == "Quỹ dự phòng"

    def test_update_saving_goal(self, client, user_a):
        created = client.post(
            GOALS_URL,
            json={"name": "Mua điện thoại", "target_amount": "15000000.00"},
            headers=user_a,
        ).json()
        goal_id = created["id"]

        # Update name and target_amount
        new_deadline = (date.today() + timedelta(days=45)).isoformat()
        update_payload = {
            "name": "Mua iPhone 16 Pro",
            "target_amount": "28000000.00",
            "deadline": new_deadline,
        }
        resp = client.patch(f"{GOALS_URL}/{goal_id}", json=update_payload, headers=user_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Mua iPhone 16 Pro"
        assert Decimal(data["target_amount"]) == Decimal("28000000.00")
        assert data["days_remaining"] == 45

    def test_cannot_update_completed_goal(self, client, user_a):
        # Create a goal with 100% initial deposit (already completed)
        created = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu đã xong", "target_amount": "1000000.00", "initial_deposit": "1000000.00"},
            headers=user_a,
        ).json()
        goal_id = created["id"]
        assert created["status"] == "completed"

        # Try to update completed goal -> Must fail with 400
        resp = client.patch(
            f"{GOALS_URL}/{goal_id}",
            json={"name": "Đổi tên mục tiêu đã xong", "target_amount": "5000000.00"},
            headers=user_a,
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Mục tiêu đã hoàn thành không thể chỉnh sửa."

    def test_delete_saving_goal(self, client, user_a):
        created = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu cần xóa", "target_amount": "5000000.00"},
            headers=user_a,
        ).json()
        goal_id = created["id"]

        resp = client.delete(f"{GOALS_URL}/{goal_id}", headers=user_a)
        assert resp.status_code == 200
        assert "detail" in resp.json()

        # Check that it is deleted
        resp_check = client.get(f"{GOALS_URL}/{goal_id}", headers=user_a)
        assert resp_check.status_code == 404


class TestSavingContributions:
    """Test deposit flow and contribution history."""

    def test_deposit_flow_and_auto_completion(self, client, user_a):
        # Create a new goal for 5,000,000 VND
        goal = client.post(
            GOALS_URL,
            json={"name": "Mua tai nghe Sony", "target_amount": "5000000.00"},
            headers=user_a,
        ).json()
        goal_id = goal["id"]

        # Deposit 2,000,000 VND
        deposit_1 = client.post(
            f"{GOALS_URL}/{goal_id}/contribute",
            json={"amount": "2000000.00", "note": "Tiền thưởng dự án"},
            headers=user_a,
        )
        assert deposit_1.status_code == 200
        d1_data = deposit_1.json()
        assert Decimal(d1_data["current_amount"]) == Decimal("2000000.00")
        assert d1_data["progress_percentage"] == 40.0
        assert d1_data["status"] == "active"
        assert len(d1_data["contributions"]) == 1
        assert d1_data["contributions"][0]["note"] == "Tiền thưởng dự án"

        # Deposit remaining 3,000,000 VND -> Reaches 100% -> Auto complete
        deposit_2 = client.post(
            f"{GOALS_URL}/{goal_id}/contribute",
            json={"amount": "3000000.00", "note": "Trích tiết kiệm tháng 8"},
            headers=user_a,
        )
        assert deposit_2.status_code == 200
        d2_data = deposit_2.json()
        assert Decimal(d2_data["current_amount"]) == Decimal("5000000.00")
        assert d2_data["progress_percentage"] == 100.0
        assert d2_data["status"] == "completed"
        assert len(d2_data["contributions"]) == 2

        # Deposit again into completed goal -> Must fail with 400
        deposit_3 = client.post(
            f"{GOALS_URL}/{goal_id}/contribute",
            json={"amount": "100000.00"},
            headers=user_a,
        )
        assert deposit_3.status_code == 400
        assert deposit_3.json()["detail"] == "Mục tiêu đã hoàn thành, không thể nạp thêm tiền."

    def test_deposit_validation(self, client, user_a):
        goal = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu test validate", "target_amount": "1000000.00"},
            headers=user_a,
        ).json()
        goal_id = goal["id"]

        # Amount <= 0
        resp = client.post(
            f"{GOALS_URL}/{goal_id}/contribute",
            json={"amount": "0.00"},
            headers=user_a,
        )
        assert resp.status_code == 422

        resp_neg = client.post(
            f"{GOALS_URL}/{goal_id}/contribute",
            json={"amount": "-50000.00"},
            headers=user_a,
        )
        assert resp_neg.status_code == 422

    def test_public_api_rejects_forged_income_allocation(self, client):
        user = register_and_login(
            client,
            "forged_allocation_user",
            "forged_allocation@example.com",
            add_income=False,
        )
        income_category = client.post(
            "/api/v1/categories",
            json={
                "name": "Thu nhập giới hạn",
                "type": "income",
                "icon": "other",
                "color": "#10B981",
            },
            headers=user,
        ).json()
        income = client.post(
            "/api/v1/transactions",
            json={
                "amount": "100000.00",
                "type": "income",
                "category_id": income_category["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user,
        ).json()
        goal = client.post(
            GOALS_URL,
            json={"name": "Không được tạo tiền ảo", "target_amount": "2000000.00"},
            headers=user,
        ).json()

        response = client.post(
            f"{GOALS_URL}/{goal['id']}/contribute",
            json={
                "amount": "1000000.00",
                "source": "income_allocation",
                "transaction_id": income["id"],
            },
            headers=user,
        )
        assert response.status_code == 422

        unchanged = client.get(f"{GOALS_URL}/{goal['id']}", headers=user).json()
        assert Decimal(unchanged["current_amount"]) == Decimal("0.00")
        assert unchanged["contributions"] == []

    def test_reactivating_cancelled_goal_requires_available_balance(self, client):
        user = register_and_login(
            client,
            "reactivate_goal_user",
            "reactivate_goal@example.com",
            add_income=False,
        )
        income_category = client.post(
            "/api/v1/categories",
            json={
                "name": "Thu để tái kích hoạt",
                "type": "income",
                "icon": "other",
                "color": "#10B981",
            },
            headers=user,
        ).json()
        expense_category = client.post(
            "/api/v1/categories",
            json={
                "name": "Chi trước tái kích hoạt",
                "type": "expense",
                "icon": "other",
                "color": "#D69A23",
            },
            headers=user,
        ).json()
        client.post(
            "/api/v1/transactions",
            json={
                "amount": "100000.00",
                "type": "income",
                "category_id": income_category["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user,
        )
        goal = client.post(
            GOALS_URL,
            json={
                "name": "Mục tiêu tạm dừng",
                "target_amount": "200000.00",
                "initial_deposit": "80000.00",
            },
            headers=user,
        ).json()
        assert client.patch(
            f"{GOALS_URL}/{goal['id']}",
            json={"status": "cancelled"},
            headers=user,
        ).status_code == 200
        assert client.post(
            "/api/v1/transactions",
            json={
                "amount": "80000.00",
                "type": "expense",
                "category_id": expense_category["id"],
                "transaction_date": date.today().isoformat(),
            },
            headers=user,
        ).status_code == 201

        response = client.patch(
            f"{GOALS_URL}/{goal['id']}",
            json={"status": "active"},
            headers=user,
        )
        assert response.status_code == 400
        assert "Không thể kích hoạt lại mục tiêu" in response.json()["detail"]
        assert client.get(
            f"{GOALS_URL}/{goal['id']}", headers=user
        ).json()["status"] == "cancelled"

    def test_deposit_to_cancelled_goal_fails(self, client, user_a):
        goal = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu sắp hủy", "target_amount": "2000000.00"},
            headers=user_a,
        ).json()
        goal_id = goal["id"]

        # Cancel goal
        client.patch(
            f"{GOALS_URL}/{goal_id}",
            json={"status": "cancelled"},
            headers=user_a,
        )

    def test_deposit_fails_when_exceeding_remaining_needed(self, client, user_a):
        goal = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu test remaining", "target_amount": "1000000.00"},
            headers=user_a,
        ).json()
        goal_id = goal["id"]

        resp = client.post(
            f"{GOALS_URL}/{goal_id}/contribute",
            json={"amount": "2000000.00"},
            headers=user_a,
        )
        assert resp.status_code == 400
        assert "vượt quá số tiền còn thiếu" in resp.json()["detail"]

    def test_deposit_fails_when_exceeding_available_balance(self, client):
        # Register a fresh user with 0 income
        fresh_user = register_and_login(client, "poor_user", "poor@example.com", add_income=False)

        goal = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu khi ví rỗng", "target_amount": "5000000.00"},
            headers=fresh_user,
        ).json()
        goal_id = goal["id"]

        resp = client.post(
            f"{GOALS_URL}/{goal_id}/contribute",
            json={"amount": "100000.00"},
            headers=fresh_user,
        )
        assert resp.status_code == 400
        assert "vượt quá số dư khả dụng" in resp.json()["detail"]

    def test_phantom_balance_prevention_across_multiple_goals(self, client):
        # Register a fresh user with 0 income, then add exactly 20,000,000 income
        limited_user = register_and_login(client, "phantom_user", "phantom@example.com", add_income=False)
        cat_resp = client.post(
            "/api/v1/categories",
            json={"name": "Lương Phantom", "type": "income", "icon": "other", "color": "#10B981"},
            headers=limited_user,
        )
        cat_id = cat_resp.json()["id"]
        client.post(
            "/api/v1/transactions",
            json={
                "amount": "20000000.00",
                "type": "income",
                "category_id": cat_id,
                "transaction_date": date.today().isoformat(),
                "description": "Lương tháng",
            },
            headers=limited_user,
        )

        # Create Goal 1 with 12,000,000 deposit
        g1 = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu 1", "target_amount": "15000000.00", "initial_deposit": "12000000.00"},
            headers=limited_user,
        ).json()

        # Remaining available balance is 20m - 12m = 8m
        # Attempt to create Goal 2 with 9,000,000 deposit -> should fail
        resp_fail = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu 2 vượt số dư", "target_amount": "10000000.00", "initial_deposit": "9000000.00"},
            headers=limited_user,
        )
        assert resp_fail.status_code == 400
        assert "vượt quá số dư khả dụng" in resp_fail.json()["detail"]

        # Create Goal 2 with 5,000,000 deposit -> success (3m left)
        g2 = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu 2", "target_amount": "10000000.00", "initial_deposit": "5000000.00"},
            headers=limited_user,
        ).json()

        # Attempt to contribute 4m to Goal 2 -> fails (only 3m left)
        resp_contrib_fail = client.post(
            f"{GOALS_URL}/{g2['id']}/contribute",
            json={"amount": "4000000.00"},
            headers=limited_user,
        )
        assert resp_contrib_fail.status_code == 400
        assert "vượt quá số dư khả dụng" in resp_contrib_fail.json()["detail"]

        # Contribute 3m to Goal 2 -> success (0m left)
        resp_contrib_ok = client.post(
            f"{GOALS_URL}/{g2['id']}/contribute",
            json={"amount": "3000000.00"},
            headers=limited_user,
        )
        assert resp_contrib_ok.status_code == 200

        # Attempt 100k more -> fails
        resp_zero = client.post(
            f"{GOALS_URL}/{g1['id']}/contribute",
            json={"amount": "100000.00"},
            headers=limited_user,
        )
        assert resp_zero.status_code == 400

        # Delete Goal 2 (releasing 8,000,000)
        client.delete(f"{GOALS_URL}/{g2['id']}", headers=limited_user)

        # Now can contribute up to remaining needed of Goal 1 (3,000,000)
        resp_after_del = client.post(
            f"{GOALS_URL}/{g1['id']}/contribute",
            json={"amount": "3000000.00"},
            headers=limited_user,
        )
        assert resp_after_del.status_code == 200
        assert resp_after_del.json()["status"] == "completed"


class TestSavingGoalsSecurityAndIDOR:
    """Ensure strict authorization and IDOR prevention."""

    def test_unauthorized_access(self, client):
        assert client.get(GOALS_URL).status_code == 401
        assert client.post(GOALS_URL, json={"name": "Hack", "target_amount": "1000"}).status_code == 401

    def test_user_cannot_access_or_modify_other_users_goal(self, client, user_a, user_b):
        # User A creates a goal
        goal_a = client.post(
            GOALS_URL,
            json={"name": "Mục tiêu bảo mật của User A", "target_amount": "10000000.00"},
            headers=user_a,
        ).json()
        goal_id = goal_a["id"]

        # User B cannot read User A's goal
        resp_read = client.get(f"{GOALS_URL}/{goal_id}", headers=user_b)
        assert resp_read.status_code == 404

        # User B cannot update User A's goal
        resp_update = client.patch(
            f"{GOALS_URL}/{goal_id}",
            json={"name": "Bị hack tên"},
            headers=user_b,
        )
        assert resp_update.status_code == 404

        # User B cannot contribute to User A's goal
        resp_contrib = client.post(
            f"{GOALS_URL}/{goal_id}/contribute",
            json={"amount": "1000000.00"},
            headers=user_b,
        )
        assert resp_contrib.status_code == 404

        # User B cannot delete User A's goal
        resp_del = client.delete(f"{GOALS_URL}/{goal_id}", headers=user_b)
        assert resp_del.status_code == 404
