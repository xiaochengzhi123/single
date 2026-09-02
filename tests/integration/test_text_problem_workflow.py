from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import create_authenticated_headers


def test_case_a_text_convolution_workflow() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client)
        response = client.post(
            "/api/v1/chat",
            headers=headers,
            json={
                "content": (
                    "已知连续时间 LTI 系统，x(t)=e^{-2t}u(t)，h(t)=e^{-t}u(t)，求零状态响应 y(t)。"
                ),
                "mode": "full_solution",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["classification"]["chapter"] == "lti"
    assert "convolution" in body["classification"]["topics"]
    assert "0" in body["solution"]["derivation_steps"][1]["expression_latex"]
    assert "u\\left(t\\right)" in body["solution"]["candidate_answer_latex"]
    assert "最终答案" in body["answer"]
