from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import create_authenticated_headers

ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


def test_admin_creates_account_and_student_can_log_in() -> None:
    username = f"issued-{uuid4().hex[:12]}"
    password = "Issued-password-2026"
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/admin/accounts",
            headers=ADMIN_HEADERS,
            json={
                "username": username,
                "display_name": "张同学",
                "password": password,
            },
        )
        wrong_password = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "Wrong-password-2026"},
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        profile = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )

    assert created.status_code == 201
    assert created.json()["username"] == username
    assert created.json()["expired"] is False
    assert created.json()["remaining_days"] > 0
    assert created.json()["expires_at"]
    assert "password" not in created.json()
    assert wrong_password.status_code == 401
    assert login.status_code == 200
    assert profile.status_code == 200
    assert profile.json()["id"] == created.json()["id"]
    assert profile.json()["display_name"] == "张同学"


def test_public_account_registration_does_not_exist() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "not-allowed",
                "display_name": "不能自助注册",
                "password": "Password-2026",
            },
        )

    assert response.status_code == 404


def test_admin_key_is_required_and_duplicate_username_is_rejected() -> None:
    username = f"duplicate-{uuid4().hex[:10]}"
    payload = {
        "username": username,
        "display_name": "重复账号测试",
        "password": "Password-2026",
    }
    with TestClient(app) as client:
        unauthorized = client.post("/api/v1/admin/accounts", json=payload)
        first = client.post("/api/v1/admin/accounts", headers=ADMIN_HEADERS, json=payload)
        duplicate = client.post("/api/v1/admin/accounts", headers=ADMIN_HEADERS, json=payload)

    assert unauthorized.status_code == 401
    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_reset_password_revokes_existing_login() -> None:
    new_password = "New-password-2026"
    with TestClient(app) as client:
        old_headers, account = create_authenticated_headers(client, username_prefix="reset")
        reset = client.post(
            f"/api/v1/admin/accounts/{account['id']}/reset-password",
            headers=ADMIN_HEADERS,
            json={"password": new_password},
        )
        revoked = client.get("/api/v1/auth/me", headers=old_headers)
        new_login = client.post(
            "/api/v1/auth/login",
            json={"username": account["username"], "password": new_password},
        )

    assert reset.status_code == 200
    assert revoked.status_code == 401
    assert new_login.status_code == 200


def test_disabling_account_revokes_existing_login() -> None:
    with TestClient(app) as client:
        headers, account = create_authenticated_headers(client, username_prefix="disabled")
        disabled = client.patch(
            f"/api/v1/admin/accounts/{account['id']}",
            headers=ADMIN_HEADERS,
            json={"active": False},
        )
        revoked = client.get("/api/v1/auth/me", headers=headers)

    assert disabled.status_code == 200
    assert disabled.json()["active"] is False
    assert revoked.status_code == 401


def test_admin_can_renew_an_account_by_whole_months() -> None:
    with TestClient(app) as client:
        _, account = create_authenticated_headers(client, username_prefix="renew")
        renewed = client.post(
            f"/api/v1/admin/accounts/{account['id']}/renew",
            headers=ADMIN_HEADERS,
            json={"months": 3},
        )

    assert renewed.status_code == 200
    assert renewed.json()["expires_at"] > account["expires_at"]
    assert renewed.json()["expired"] is False
