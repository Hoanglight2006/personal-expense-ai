import random
import string
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.category_defaults import DEFAULT_CATEGORIES
from app.core.security import get_password_hash
from app.models.category import Category
from app.models.user import User
from tests.test_db import TestingSessionLocal
import app.api.routes.auth as auth_routes


def random_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def test_register_user(client: TestClient):
    username = random_string()
    email = f"{username}@example.com"
    password = "strongpassword123"

    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == username
    assert data["email"] == email.lower()
    assert "id" in data
    db = TestingSessionLocal()
    try:
        defaults = db.query(Category).filter(Category.user_id == data["id"]).all()
        assert len(defaults) == len(DEFAULT_CATEGORIES)
        assert all(category.is_default for category in defaults)
    finally:
        db.close()


def test_register_duplicate_username(client: TestClient):
    username = random_string()
    email1 = f"{username}1@example.com"
    email2 = f"{username}2@example.com"
    password = "strongpassword123"

    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email1, "password": password},
    )
    assert response.status_code == 201

    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email2, "password": password},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already exists."


def test_register_duplicate_email_uses_generic_message(client: TestClient):
    username = random_string()
    email = f"{username}@example.com"
    payload = {"username": username, "email": email, "password": "strongpassword123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    response = client.post(
        "/api/v1/auth/register",
        json={**payload, "username": f"{username}2"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already exists."


def test_register_integrity_error_rolls_back_and_uses_generic_message(client: TestClient):
    with patch.object(
        Session,
        "commit",
        side_effect=IntegrityError("duplicate", {}, Exception()),
    ):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": random_string(),
                "email": f"{random_string()}@example.com",
                "password": "strongpassword123",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already exists."


def test_register_normalizes_username_and_email(client: TestClient):
    username = random_string()
    response = client.post(
        "/api/v1/auth/register",
        json={"username": f"  {username}  ", "email": f"  {username.upper()}@EXAMPLE.COM ", "password": "strongpassword123"},
    )
    assert response.status_code == 201
    assert response.json()["username"] == username
    assert response.json()["email"] == f"{username.lower()}@example.com"


def test_register_rejects_password_over_bcrypt_limit(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": random_string(), "email": f"{random_string()}@example.com", "password": "a" * 73},
    )
    assert response.status_code == 422


def test_login_success(client: TestClient):
    username = random_string()
    email = f"{username}@example.com"
    password = "strongpassword123"

    # Register
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])["sub"].isdigit()


def test_login_success_with_email(client: TestClient):
    username = random_string()
    email = f"{username}@example.com"
    password = "strongpassword123"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": email.upper(), "password": password},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_register_rejects_short_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": random_string(), "email": f"{random_string()}@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_forgot_and_reset_password_flow(client: TestClient, monkeypatch):
    username = random_string()
    email = f"{username}@example.com"
    old_password = "strongpassword123"
    new_password = "newstrongpassword456"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": old_password},
    )
    sent = {}

    def capture_email(to_email: str, reset_url: str):
        sent["to"] = to_email
        sent["url"] = reset_url

    monkeypatch.setattr(auth_routes, "send_password_reset_email", capture_email)
    response = client.post("/api/v1/auth/forgot-password", json={"email": email.upper()})
    assert response.status_code == 200
    assert response.json()["message"].startswith("Nếu email tồn tại")
    token = parse_qs(urlparse(sent["url"]).query)["token"][0]

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": new_password},
    )
    assert reset.status_code == 200
    assert client.post("/api/v1/auth/login", data={"username": username, "password": old_password}).status_code == 401
    assert client.post("/api/v1/auth/login", data={"username": username, "password": new_password}).status_code == 200
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "password": old_password}).status_code == 400


def test_login_wrong_password(client: TestClient):
    username = random_string()
    email = f"{username}@example.com"
    password = "strongpassword123"

    # Register
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_get_current_user(client: TestClient):
    username = random_string()
    email = f"{username}@example.com"
    password = "strongpassword123"

    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username
    assert data["email"] == email.lower()


def test_update_current_user_profile(client: TestClient):
    username = random_string()
    password = "strongpassword123"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": password},
    )
    token = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    ).json()["access_token"]

    response = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": f"  {username}new  ", "email": f"  {username}NEW@EXAMPLE.COM  "},
    )

    assert response.status_code == 200
    assert response.json()["username"] == f"{username}new"
    assert response.json()["email"] == f"{username.lower()}new@example.com"


def test_update_current_user_rejects_duplicate(client: TestClient):
    first = random_string()
    second = random_string()
    password = "strongpassword123"
    for username in (first, second):
        client.post(
            "/api/v1/auth/register",
            json={"username": username, "email": f"{username}@example.com", "password": password},
        )
    token = client.post(
        "/api/v1/auth/login", data={"username": first, "password": password}
    ).json()["access_token"]

    response = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": f"{second}@example.com"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already exists."


def test_change_password_for_current_user(client: TestClient):
    username = random_string()
    old_password = "strongpassword123"
    new_password = "newstrongpassword456"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": old_password},
    )
    token = client.post(
        "/api/v1/auth/login", data={"username": username, "password": old_password}
    ).json()["access_token"]

    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": old_password, "new_password": new_password},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Đổi mật khẩu thành công."
    assert client.post("/api/v1/auth/login", data={"username": username, "password": old_password}).status_code == 401
    assert client.post("/api/v1/auth/login", data={"username": username, "password": new_password}).status_code == 200


def test_change_password_rejects_wrong_current_password(client: TestClient):
    username = random_string()
    password = "strongpassword123"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": password},
    )
    token = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    ).json()["access_token"]

    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "wrongpassword", "new_password": "newstrongpassword456"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Mật khẩu hiện tại không chính xác."


def test_get_current_user_no_token(client: TestClient):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_cors_allows_frontend_origin(client: TestClient):
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_get_current_user_invalid_token(client: TestClient):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_get_current_user_expired_token(client: TestClient):
    token = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_get_current_user_missing_sub(client: TestClient):
    token = jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_get_current_user_deleted_user(client: TestClient):
    username = random_string()
    client.post("/api/v1/auth/register", json={"username": username, "email": f"{username}@example.com", "password": "strongpassword123"})
    login = client.post("/api/v1/auth/login", data={"username": username, "password": "strongpassword123"})
    token = login.json()["access_token"]
    from tests.test_db import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        db.query(User).filter(User.username == username).delete()
        db.commit()
    finally:
        db.close()
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_update_avatar_preset_url(client: TestClient):
    username = random_string()
    client.post("/api/v1/auth/register", json={"username": username, "email": f"{username}@example.com", "password": "strongpassword123"})
    login = client.post("/api/v1/auth/login", data={"username": username, "password": "strongpassword123"})
    token = login.json()["access_token"]

    response = client.patch(
        "/api/v1/auth/me",
        json={"avatar_url": "/assets/mascot_coin.png"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] == "/assets/mascot_coin.png"


def test_upload_avatar_image_file(client: TestClient):
    username = random_string()
    client.post("/api/v1/auth/register", json={"username": username, "email": f"{username}@example.com", "password": "strongpassword123"})
    login = client.post("/api/v1/auth/login", data={"username": username, "password": "strongpassword123"})
    token = login.json()["access_token"]

    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    files = {"file": ("avatar.png", fake_png, "image/png")}

    response = client.post(
        "/api/v1/auth/avatar/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] is not None
    assert "/static/avatars/avatar_" in data["avatar_url"]


def test_upload_avatar_invalid_type(client: TestClient):
    username = random_string()
    client.post("/api/v1/auth/register", json={"username": username, "email": f"{username}@example.com", "password": "strongpassword123"})
    login = client.post("/api/v1/auth/login", data={"username": username, "password": "strongpassword123"})
    token = login.json()["access_token"]

    files = {"file": ("document.pdf", b"%PDF-1.4...", "application/pdf")}

    response = client.post(
        "/api/v1/auth/avatar/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "Định dạng ảnh không hợp lệ" in response.json()["detail"]

