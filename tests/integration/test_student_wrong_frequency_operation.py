from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import create_authenticated_headers


def test_case_d_reviews_first_wrong_step() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client)
        response = client.post(
            "/api/v1/chat",
            headers=headers,
            json={
                "content": "已知 LTI 系统，求零状态响应。",
                "student_work": "Y(s)=X(s)+H(s)",
                "mode": "review_student_work",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verification_failed"
    assert body["verification"]["issues"][0]["code"] == "wrong_frequency_domain_operation"
    assert "Y(s)=X(s)H(s)" in body["answer"]
