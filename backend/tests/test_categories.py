from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from conftest import TestingSessionLocal


def auth_headers(client: TestClient) -> tuple[dict[str, str], int]:
    suffix = uuid4().hex[:12]
    username = f"cat{suffix}"
    password = "strongpassword123"
    register = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200
    user_id = register.json()["id"]
    db = TestingSessionLocal()
    try:
        db.query(Category).filter(Category.user_id == user_id).delete()
        db.commit()
    finally:
        db.close()
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user_id


def create_category(
    client: TestClient,
    headers: dict[str, str],
    name: str,
    icon: str = "food",
    color: str = "#C87941",
):
    return client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": name, "icon": icon, "color": color},
    )


def test_create_category_trims_name_and_validates_input(client: TestClient):
    headers, _ = auth_headers(client)
    response = create_category(client, headers, "  Ăn uống  ")
    assert response.status_code == 201
    assert response.json()["name"] == "Ăn uống"
    assert response.json()["color"] == "#C87941"
    assert response.json()["is_active"] is True

    assert create_category(client, headers, "   ").status_code == 422
    assert create_category(client, headers, "Đi lại", icon="../../secret").status_code == 422
    assert create_category(client, headers, "Đi lại", color="red").status_code == 422


def test_create_default_categories_adds_only_missing_presets(client: TestClient):
    headers, _ = auth_headers(client)
    assert create_category(client, headers, "Ăn uống", icon="food").status_code == 201
    response = client.post("/api/v1/categories/defaults", headers=headers)
    assert response.status_code == 201
    assert len(response.json()) == 11
    assert all(item["is_default"] is True for item in response.json())
    assert client.post("/api/v1/categories/defaults", headers=headers).json() == []
    items = client.get(
        "/api/v1/categories", headers=headers, params={"status": "all"}
    ).json()["items"]
    assert len(items) == 12


def test_category_name_uniqueness_is_case_insensitive(client: TestClient):
    headers, _ = auth_headers(client)
    assert create_category(client, headers, "Lương", icon="salary").status_code == 201
    duplicate = create_category(client, headers, "  lƯƠnG  ", icon="salary")
    assert duplicate.status_code == 409
    assert create_category(client, headers, "Lương thưởng", icon="bonus").status_code == 201


def test_unicode_casefold_expansion_fits_normalized_storage(client: TestClient):
    headers, _ = auth_headers(client)
    name = "ß" * 50
    response = create_category(client, headers, name)
    assert response.status_code == 201
    assert response.json()["name"] == name


def test_database_rejects_transaction_with_category_from_another_owner(client: TestClient):
    first_headers, first_user_id = auth_headers(client)
    second_headers, _ = auth_headers(client)
    foreign_category = create_category(client, second_headers, "Danh mục người khác").json()

    db = TestingSessionLocal()
    try:
        db.add(Transaction(
            user_id=first_user_id,
            category_id=foreign_category["id"],
            type=CategoryType.EXPENSE,
            amount=Decimal("1.00"),
            transaction_date=date(2026, 8, 1),
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_update_rejects_conflict_and_invalid_empty_patch(client: TestClient):
    headers, _ = auth_headers(client)
    first = create_category(client, headers, "Ăn uống").json()
    second = create_category(client, headers, "Đi lại", icon="transport").json()

    conflict = client.patch(
        f"/api/v1/categories/{second['id']}",
        headers=headers,
        json={"name": "  ĂN UỐNG "},
    )
    assert conflict.status_code == 409
    assert client.patch(
        f"/api/v1/categories/{first['id']}", headers=headers, json={}
    ).status_code == 422

    updated = client.patch(
        f"/api/v1/categories/{second['id']}",
        headers=headers,
        json={"name": "  Xăng xe ", "color": "#123abc"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Xăng xe"
    assert updated.json()["color"] == "#123ABC"


def test_owner_isolation_for_list_detail_update_hide_and_restore(client: TestClient):
    owner_headers, _ = auth_headers(client)
    other_headers, _ = auth_headers(client)
    category = create_category(client, owner_headers, "Riêng tư").json()

    other_list = client.get("/api/v1/categories", headers=other_headers)
    assert other_list.status_code == 200
    assert all(item["id"] != category["id"] for item in other_list.json()["items"])

    assert client.get(
        f"/api/v1/categories/{category['id']}", headers=other_headers
    ).status_code == 404
    assert client.patch(
        f"/api/v1/categories/{category['id']}",
        headers=other_headers,
        json={"name": "Chiếm quyền"},
    ).status_code == 404
    assert client.post(
        f"/api/v1/categories/{category['id']}/hide", headers=other_headers
    ).status_code == 404
    assert client.post(
        f"/api/v1/categories/{category['id']}/restore", headers=other_headers
    ).status_code == 404


def test_search_status_filters_and_restore(client: TestClient):
    headers, _ = auth_headers(client)
    food = create_category(client, headers, "Ăn uống", icon="food").json()
    create_category(client, headers, "Lương", icon="salary")
    hidden = create_category(client, headers, "Mua sắm", icon="shopping").json()
    assert client.post(
        f"/api/v1/categories/{hidden['id']}/hide", headers=headers
    ).status_code == 200

    active = client.get("/api/v1/categories", headers=headers).json()["items"]
    assert {item["name"] for item in active} == {"Ăn uống", "Lương"}
    searched = client.get(
        "/api/v1/categories", headers=headers, params={"search": "ăn", "status": "all"}
    ).json()["items"]
    assert [item["id"] for item in searched] == [food["id"]]
    hidden_items = client.get(
        "/api/v1/categories", headers=headers, params={"status": "hidden"}
    ).json()["items"]
    assert [item["id"] for item in hidden_items] == [hidden["id"]]

    restored = client.post(
        f"/api/v1/categories/{hidden['id']}/restore", headers=headers
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True


def test_hide_is_soft_delete_and_keeps_historical_transaction(client: TestClient):
    headers, user_id = auth_headers(client)
    category = create_category(client, headers, "Y tế", icon="health").json()
    db = TestingSessionLocal()
    try:
        transaction = Transaction(
            user_id=user_id,
            category_id=category["id"],
            type=CategoryType.EXPENSE,
            amount=Decimal("125.50"),
            description="Dữ liệu giả",
            transaction_date=date(2026, 8, 15),
        )
        db.add(transaction)
        db.commit()
        transaction_id = transaction.id
    finally:
        db.close()

    assert client.post(
        f"/api/v1/categories/{category['id']}/hide", headers=headers
    ).status_code == 200
    db = TestingSessionLocal()
    try:
        assert db.query(Transaction).filter(Transaction.id == transaction_id).one().amount == Decimal("125.50")
    finally:
        db.close()
    stats = client.get(
        "/api/v1/categories/statistics",
        headers=headers,
        params={"start_date": "2026-08-01", "end_date": "2026-08-31"},
    ).json()["items"]
    item = next(item for item in stats if item["id"] == category["id"])
    assert item["total_amount"] == "125.50"
    assert item["transaction_count"] == 1

    type_patch_resp = client.patch(
        f"/api/v1/categories/{category['id']}",
        headers=headers,
        json={"type": "income"},
    )
    assert type_patch_resp.status_code == 200
    assert type_patch_resp.json()["type"] == "income"


def test_statistics_sort_percentage_date_boundary_and_user_isolation(client: TestClient):
    headers, user_id = auth_headers(client)
    other_headers, other_user_id = auth_headers(client)
    food = create_category(client, headers, "Ăn uống", icon="food").json()
    home = create_category(client, headers, "Nhà ở", icon="home").json()
    salary = create_category(client, headers, "Lương", icon="salary").json()
    other = create_category(client, other_headers, "Không được trộn", icon="other").json()

    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                Transaction(user_id=user_id, category_id=food["id"], type=CategoryType.EXPENSE, amount=Decimal("100.00"), transaction_date=date(2026, 8, 1)),
                Transaction(user_id=user_id, category_id=home["id"], type=CategoryType.EXPENSE, amount=Decimal("300.00"), transaction_date=date(2026, 8, 31)),
                Transaction(user_id=user_id, category_id=salary["id"], type=CategoryType.INCOME, amount=Decimal("500.00"), transaction_date=date(2026, 8, 15)),
                Transaction(user_id=other_user_id, category_id=other["id"], type=CategoryType.EXPENSE, amount=Decimal("9999.00"), transaction_date=date(2026, 8, 15)),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/v1/categories",
        headers=headers,
        params={
            "status": "all",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "sort": "amount_desc",
        },
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["name"] for item in items] == ["Lương", "Nhà ở", "Ăn uống"]
    values = {item["name"]: item for item in items}
    assert values["Ăn uống"]["expense_percentage"] == "25.00"
    assert values["Ăn uống"]["expense_amount"] == "100.00"
    assert values["Ăn uống"]["income_amount"] == "0.00"
    assert values["Nhà ở"]["expense_percentage"] == "75.00"
    assert values["Lương"]["expense_percentage"] == "0.00"
    assert values["Lương"]["income_amount"] == "500.00"
    assert values["Nhà ở"]["transaction_count"] == 1
    assert all(item["total_amount"] != "9999.00" for item in items)

    ascending = client.get(
        "/api/v1/categories",
        headers=headers,
        params={"start_date": "2026-08-01", "end_date": "2026-08-31", "sort": "amount_asc"},
    ).json()["items"]
    assert [item["name"] for item in ascending] == ["Ăn uống", "Nhà ở", "Lương"]


def test_zero_expense_returns_zero_percentage_and_invalid_period_is_rejected(client: TestClient):
    headers, _ = auth_headers(client)
    create_category(client, headers, "Chưa chi", icon="other")
    response = client.get(
        "/api/v1/categories",
        headers=headers,
        params={"start_date": "2026-08-01", "end_date": "2026-08-31"},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["expense_percentage"] == "0.00"
    invalid = client.get(
        "/api/v1/categories",
        headers=headers,
        params={"start_date": "2026-09-01", "end_date": "2026-08-31"},
    )
    assert invalid.status_code == 422


def test_restore_rechecks_legacy_name_conflict(client: TestClient):
    headers, _ = auth_headers(client)
    hidden = create_category(client, headers, "Tên cũ").json()
    active = create_category(client, headers, "Tên đang dùng").json()
    client.post(f"/api/v1/categories/{hidden['id']}/hide", headers=headers)

    db = TestingSessionLocal()
    try:
        legacy_category = db.query(Category).filter(Category.id == hidden["id"]).one()
        legacy_category.name = active["name"]
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/api/v1/categories/{hidden['id']}/restore", headers=headers
    )
    assert response.status_code == 409


def test_create_income_category_persists_type(client: TestClient):
    headers, _ = auth_headers(client)
    res = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Lương tháng", "type": "income", "icon": "salary", "color": "#10B981"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Lương tháng"
    assert data["type"] == "income"


def test_category_stats_excludes_soft_deleted_transactions(client: TestClient):
    headers, user_id = auth_headers(client)
    cat = create_category(client, headers, "Mua sắm", icon="shopping").json()
    db = TestingSessionLocal()
    try:
        active_txn = Transaction(
            user_id=user_id,
            category_id=cat["id"],
            type=CategoryType.EXPENSE,
            amount=Decimal("100.00"),
            transaction_date=date(2026, 8, 10),
            is_deleted=False,
        )
        deleted_txn = Transaction(
            user_id=user_id,
            category_id=cat["id"],
            type=CategoryType.EXPENSE,
            amount=Decimal("500.00"),
            transaction_date=date(2026, 8, 11),
            is_deleted=True,
        )
        db.add_all([active_txn, deleted_txn])
        db.commit()
    finally:
        db.close()

    res = client.get(
        "/api/v1/categories",
        headers=headers,
        params={"start_date": "2026-08-01", "end_date": "2026-08-31"},
    )
    assert res.status_code == 200
    item = next(i for i in res.json()["items"] if i["id"] == cat["id"])
    assert item["total_amount"] == "100.00"
    assert item["transaction_count"] == 1


def test_soft_deleted_category_cannot_be_accessed_or_modified(client: TestClient):
    headers, _ = auth_headers(client)
    cat = create_category(client, headers, "Tập gym", icon="sports").json()
    cat_id = cat["id"]

    # Delete category
    del_res = client.delete(f"/api/v1/categories/{cat_id}", headers=headers)
    assert del_res.status_code == 204

    # GET /api/v1/categories/{id} should return 404
    get_res = client.get(f"/api/v1/categories/{cat_id}", headers=headers)
    assert get_res.status_code == 404

    # PATCH /api/v1/categories/{id} should return 404
    patch_res = client.patch(
        f"/api/v1/categories/{cat_id}",
        headers=headers,
        json={"name": "Tập gym VIP"},
    )
    assert patch_res.status_code == 404

    # POST /api/v1/categories/{id}/hide should return 404
    hide_res = client.post(f"/api/v1/categories/{cat_id}/hide", headers=headers)
    assert hide_res.status_code == 404

    # POST /api/v1/categories/{id}/restore should return 404
    restore_res = client.post(f"/api/v1/categories/{cat_id}/restore", headers=headers)
    assert restore_res.status_code == 404


