from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import create_authenticated_headers


def test_case_c_missing_roc_is_not_guessed() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client)
        response = client.post(
            "/api/v1/chat",
            headers=headers,
            json={"content": "已知 X(z)=z/(z-a)，求对应的时域序列 x[n]。", "mode": "full_solution"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert "ROC" in body["answer"]
    assert "因果" in body["answer"]
