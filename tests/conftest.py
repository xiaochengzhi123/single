from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

# Test runs must never inherit a developer's real Model Studio credentials from .env.
os.environ["DASHSCOPE_API_KEY"] = ""
os.environ["USE_FAKE_MODELS"] = "true"
TEST_LEARNING_STORE = Path(tempfile.gettempdir()) / f"signaltutor-test-learning-{os.getpid()}.json"
os.environ["LEARNING_STORE_PATH"] = str(TEST_LEARNING_STORE)
TEST_ACCOUNT_STORE = Path(tempfile.gettempdir()) / f"signaltutor-test-accounts-{os.getpid()}.json"
os.environ["ACCOUNT_STORE_PATH"] = str(TEST_ACCOUNT_STORE)
os.environ["AUTH_SECRET"] = "test-auth-secret-that-is-not-used-outside-pytest"
os.environ["ADMIN_API_KEY"] = "test-admin-key"


def create_authenticated_headers(
    client: TestClient,
    *,
    username_prefix: str = "student",
    password: str = "Test-password-2026",
) -> tuple[dict[str, str], dict]:
    username = f"{username_prefix}-{uuid4().hex[:12]}"
    created = client.post(
        "/api/v1/admin/accounts",
        headers={"X-Admin-Key": "test-admin-key"},
        json={
            "username": username,
            "display_name": f"测试学生 {username[-4:]}",
            "password": password,
        },
    )
    assert created.status_code == 201, created.text
    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, created.json()


def pytest_sessionfinish() -> None:
    TEST_LEARNING_STORE.unlink(missing_ok=True)
    TEST_ACCOUNT_STORE.unlink(missing_ok=True)
