from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import create_authenticated_headers


def test_fast_chat_returns_exam_metadata_shape() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client)
        response = client.post(
            "/api/v1/chat/answer",
            headers=headers,
            json={"content": "判断离散正弦序列是否具有周期性"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["problem_id"]
    assert body["response_kind"] == "solve"
    assert body["chapter"] == "signals"
    assert isinstance(body["exam_points"], list)
    assert isinstance(body["common_mistakes"], list)


def test_fast_chat_accepts_conversation_history() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client)
        response = client.post(
            "/api/v1/chat/answer",
            headers=headers,
            json={
                "content": "为什么它不是时不变的？",
                "history": [
                    {"role": "user", "content": "判断 y(t)=x(2t) 是否时不变"},
                    {"role": "assistant", "content": "结论：它是时变系统。"},
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["problem_id"]


def test_answer_feedback_is_recorded() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client)
        answer = client.post(
            "/api/v1/chat/answer",
            headers=headers,
            json={"content": "说明卷积的定义"},
        )
        response = client.post(
            "/api/v1/feedback",
            headers=headers,
            json={
                "problem_id": answer.json()["problem_id"],
                "rating": "helpful",
            },
        )

    assert answer.status_code == 200
    assert response.status_code == 201
    assert response.json() == {"status": "recorded"}


def test_learning_records_are_isolated_between_accounts() -> None:
    with TestClient(app) as client:
        first_headers, first_account = create_authenticated_headers(
            client, username_prefix="first"
        )
        second_headers, second_account = create_authenticated_headers(
            client, username_prefix="second"
        )
        saved = client.post(
            "/api/v1/mistakes",
            headers=first_headers,
            json={
                "problem_id": "isolated-problem",
                "question": "隔离测试：求系统冲激响应",
                "answer_markdown": "隔离测试答案",
                "chapter": "lti",
                "topics": ["impulse_response"],
                "common_mistakes": [],
            },
        )
        first_overview = client.get("/api/v1/students/me/overview", headers=first_headers)
        second_overview = client.get("/api/v1/students/me/overview", headers=second_headers)

    assert saved.status_code == 201
    assert first_overview.json()["student_id"] == first_account["id"]
    assert second_overview.json()["student_id"] == second_account["id"]
    assert any(
        row["question"] == "隔离测试：求系统冲激响应"
        for row in first_overview.json()["mistakes"]
    )
    assert second_overview.json()["mistakes"] == []


def test_chat_requires_login() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/answer",
            json={"content": "测试"},
        )

    assert response.status_code == 401
    assert response.json()["detail"]["message"] == "请先登录"


def test_mistake_book_is_reflected_in_learning_overview() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client)
        saved = client.post(
            "/api/v1/mistakes",
            headers=headers,
            json={
                "problem_id": "problem-1",
                "question": "求卷积积分",
                "answer_markdown": "标准解答",
                "chapter": "lti",
                "topics": ["convolution"],
                "common_mistakes": ["积分上下限错误"],
            },
        )
        overview = client.get("/api/v1/students/me/overview", headers=headers)
        updated = client.patch(
            f"/api/v1/mistakes/{saved.json()['id']}",
            headers=headers,
            json={"mastered": True},
        )

    assert saved.status_code == 201
    assert overview.status_code == 200
    assert overview.json()["open_mistakes"] == 1
    assert overview.json()["topics"] == []
    assert updated.status_code == 200
    assert updated.json()["mastered"] is True
