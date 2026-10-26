import random
import string
import pytest
from fastapi.testclient import TestClient

from app.models.enums import UserRole
from app.models.user import User
from tests.test_db import TestingSessionLocal


def random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def create_user_helper(client: TestClient, role: UserRole = UserRole.USER):
    username = f"u_{random_string()}"
    email = f"{username}@test.com"
    password = "Password123@"

    resp = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    user_data = resp.json()

    if role == UserRole.ADMIN:
        db = TestingSessionLocal()
        try:
            db_user = db.query(User).filter(User.id == user_data["id"]).first()
            db_user.role = UserRole.ADMIN
            db.commit()
        finally:
            db.close()

    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    return {
        "id": user_data["id"],
        "username": username,
        "email": email,
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_regular_user_cannot_access_admin_routes(client: TestClient):
    reg = create_user_helper(client, UserRole.USER)

    # All admin endpoints must return 403 Forbidden for standard user
    resp = client.get("/api/v1/admin/users", headers=reg["headers"])
    assert resp.status_code == 403

    resp = client.get("/api/v1/admin/stats", headers=reg["headers"])
    assert resp.status_code == 403

    resp = client.patch(
        f"/api/v1/admin/users/{reg['id']}/status",
        headers=reg["headers"],
        json={"is_locked": True},
    )
    assert resp.status_code == 403


def test_admin_list_users_and_stats(client: TestClient):
    admin = create_user_helper(client, UserRole.ADMIN)
    reg = create_user_helper(client, UserRole.USER)

    # 1. List users
    resp = client.get("/api/v1/admin/users", headers=admin["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 2
    assert data["active_count"] >= 2

    # Check search filter
    resp = client.get(
        f"/api/v1/admin/users?search={reg['username']}",
        headers=admin["headers"],
    )
    assert resp.status_code == 200
    search_data = resp.json()
    assert len(search_data["items"]) >= 1
    assert search_data["items"][0]["email"] == reg["email"].lower()

    # 2. System stats
    resp = client.get("/api/v1/admin/stats", headers=admin["headers"])
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_users"] >= 2
    assert "ai_reports_by_type" in stats


def test_admin_lock_and_unlock_user(client: TestClient):
    admin = create_user_helper(client, UserRole.ADMIN)
    reg = create_user_helper(client, UserRole.USER)
    target_id = reg["id"]

    # 1. Lock user
    lock_resp = client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        headers=admin["headers"],
        json={"is_locked": True},
    )
    assert lock_resp.status_code == 200
    assert lock_resp.json()["is_locked"] is True

    # 2. Attempt login as locked user -> Must fail with 403
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": reg["username"], "password": reg["password"]},
    )
    assert login_resp.status_code == 403
    assert "tạm khóa" in login_resp.json()["detail"]

    # 3. Unlock user
    unlock_resp = client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        headers=admin["headers"],
        json={"is_locked": False},
    )
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["is_locked"] is False

    # 4. User can now login again
    login_again = client.post(
        "/api/v1/auth/login",
        data={"username": reg["username"], "password": reg["password"]},
    )
    assert login_again.status_code == 200


def test_admin_cannot_lock_self(client: TestClient):
    admin = create_user_helper(client, UserRole.ADMIN)
    self_id = admin["id"]

    resp = client.patch(
        f"/api/v1/admin/users/{self_id}/status",
        headers=admin["headers"],
        json={"is_locked": True},
    )
    assert resp.status_code == 400
    assert "không thể tự khóa" in resp.json()["detail"]


def test_admin_reset_user_password(client: TestClient):
    admin = create_user_helper(client, UserRole.ADMIN)
    reg = create_user_helper(client, UserRole.USER)
    target_id = reg["id"]

    # Reset password
    resp = client.post(
        f"/api/v1/admin/users/{target_id}/reset-password",
        headers=admin["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "temp_password" in data
    temp_pass = data["temp_password"]

    # Old password no longer works
    old_login = client.post(
        "/api/v1/auth/login",
        data={"username": reg["username"], "password": reg["password"]},
    )
    assert old_login.status_code == 401

    # New temp password works
    new_login = client.post(
        "/api/v1/auth/login",
        data={"username": reg["username"], "password": temp_pass},
    )
    assert new_login.status_code == 200


def test_admin_provision_user_and_admin_accounts(client: TestClient):
    admin = create_user_helper(client, UserRole.ADMIN)

    # 1. Admin creates regular user
    u_name = f"new_user_{random_string()}"
    u_email = f"{u_name}@test.com"
    u_pass = "SecurePass123@"
    resp = client.post(
        "/api/v1/admin/users",
        headers=admin["headers"],
        json={
            "username": u_name,
            "email": u_email,
            "password": u_pass,
            "role": "user",
        },
    )
    assert resp.status_code == 201
    created_user = resp.json()
    assert created_user["username"] == u_name
    assert created_user["email"] == u_email.lower()
    assert created_user["role"] == "user"
    assert created_user["is_locked"] is False

    # Verify newly created user can log in
    login_user = client.post(
        "/api/v1/auth/login",
        data={"username": u_name, "password": u_pass},
    )
    assert login_user.status_code == 200

    # 2. Admin creates another Admin
    admin_name = f"new_admin_{random_string()}"
    admin_email = f"{admin_name}@test.com"
    admin_pass = "AdminSec123@"
    resp_adm = client.post(
        "/api/v1/admin/users",
        headers=admin["headers"],
        json={
            "username": admin_name,
            "email": admin_email,
            "password": admin_pass,
            "role": "admin",
        },
    )
    assert resp_adm.status_code == 201
    created_adm = resp_adm.json()
    assert created_adm["email"] == admin_email.lower()
    assert created_adm["role"] == "admin"

    # Verify new admin can log in and access admin stats
    login_adm = client.post(
        "/api/v1/auth/login",
        data={"username": admin_name, "password": admin_pass},
    )
    assert login_adm.status_code == 200
    adm_token = login_adm.json()["access_token"]
    stats_resp = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {adm_token}"})
    assert stats_resp.status_code == 200


def test_admin_provision_rejects_duplicate_or_invalid(client: TestClient):
    admin = create_user_helper(client, UserRole.ADMIN)
    reg = create_user_helper(client, UserRole.USER)

    # 1. Duplicate email
    resp = client.post(
        "/api/v1/admin/users",
        headers=admin["headers"],
        json={
            "username": f"unique_{random_string()}",
            "email": reg["email"],
            "password": "Password123@",
            "role": "user",
        },
    )
    assert resp.status_code == 409
    assert "Email" in resp.json()["detail"]

    # 2. Duplicate username
    resp2 = client.post(
        "/api/v1/admin/users",
        headers=admin["headers"],
        json={
            "username": reg["username"],
            "email": f"unique_{random_string()}@test.com",
            "password": "Password123@",
            "role": "user",
        },
    )
    assert resp2.status_code == 409
    assert "Tên người dùng" in resp2.json()["detail"]

    # 3. Regular user cannot provision
    resp3 = client.post(
        "/api/v1/admin/users",
        headers=reg["headers"],
        json={
            "username": f"hacker_{random_string()}",
            "email": f"hacker_{random_string()}@test.com",
            "password": "Password123@",
            "role": "admin",
        },
    )
    assert resp3.status_code == 403
