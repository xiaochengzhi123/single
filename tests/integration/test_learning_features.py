import base64
import json

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


def test_fast_chat_stream_returns_delta_and_completed_response() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client, username_prefix="stream")
        with client.stream(
            "POST",
            "/api/v1/chat/answer/stream",
            headers=headers,
            json={"content": "判断离散正弦序列是否具有周期性"},
        ) as response:
            events = [line for line in response.iter_lines() if line]

    assert response.status_code == 200
    assert '"type": "delta"' in events[0]
    assert '"type": "done"' in events[-1]
    assert '"problem_id"' in events[-1]


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


def test_uploaded_question_image_is_available_only_to_its_owner() -> None:
    image = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUB"
        "AScY42YAAAAASUVORK5CYII="
    )
    with TestClient(app) as client:
        owner_headers, _ = create_authenticated_headers(client, username_prefix="image-owner")
        other_headers, _ = create_authenticated_headers(client, username_prefix="image-other")
        answered = client.post(
            "/api/v1/chat/answer-image/stream",
            headers=owner_headers,
            files={"file": ("question.png", image, "image/png")},
            data={"content": "请解答图片题目"},
        )
        assert answered.status_code == 200, answered.text
        events = [json.loads(line) for line in answered.text.splitlines() if line]
        assert events[0]["type"] == "delta"
        assert events[-1]["type"] == "done"
        answer = events[-1]["response"]
        saved = client.post(
            "/api/v1/mistakes",
            headers=owner_headers,
            json={
                "problem_id": answer["problem_id"],
                "question": answer.get("recognized_question") or "图片题目",
                "answer_markdown": answer["answer_markdown"],
                "source_type": answer["source_type"],
                "chapter": answer["chapter"],
                "topics": answer["topics"],
                "common_mistakes": answer["common_mistakes"],
            },
        )
        assert saved.status_code == 201, saved.text
        mistake = saved.json()
        owner_image = client.get(
            f"/api/v1/mistakes/{mistake['id']}/image", headers=owner_headers
        )
        other_image = client.get(
            f"/api/v1/mistakes/{mistake['id']}/image", headers=other_headers
        )

    assert answer["source_type"] == "uploaded_image"
    assert mistake["has_image"] is True
    assert owner_image.status_code == 200
    assert owner_image.headers["content-type"] == "image/png"
    assert other_image.status_code == 404


def test_ai_generated_question_can_be_saved_without_an_answer() -> None:
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client, username_prefix="practice")
        saved = client.post(
            "/api/v1/mistakes",
            headers=headers,
            json={
                "problem_id": "generated-practice",
                "question": "已知离散序列，求其 Z 变换及收敛域。",
                "answer_markdown": "",
                "source_type": "ai_generated",
                "chapter": "z_transform",
                "topics": ["roc"],
                "common_mistakes": [],
            },
        )

    assert saved.status_code == 201
    assert saved.json()["source_type"] == "ai_generated"
    assert saved.json()["answer_markdown"] == ""
