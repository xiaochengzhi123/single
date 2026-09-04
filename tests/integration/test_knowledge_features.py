from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from tests.conftest import create_authenticated_headers

ADMIN_HEADERS = {"X-Admin-Key": "test-admin-key"}


def test_admin_creates_knowledge_and_student_can_search_it() -> None:
    unique = uuid4().hex[:8]
    payload = {
        "title": f"西电采样真题 {unique}",
        "content": f"{unique} 已知最高角频率，求满足采样定理的最低采样频率。",
        "kind": "past_exam",
        "school": "西安电子科技大学",
        "year": 2025,
        "chapter": "sampling",
        "topics": ["采样定理"],
        "difficulty": 3,
        "published": True,
    }
    with TestClient(app) as client:
        unauthorized = client.post("/api/v1/admin/knowledge", json=payload)
        created = client.post("/api/v1/admin/knowledge", headers=ADMIN_HEADERS, json=payload)
        student_headers, _ = create_authenticated_headers(client, username_prefix="knowledge")
        schools = client.get("/api/v1/knowledge/schools", headers=student_headers)
        search = client.get(
            "/api/v1/knowledge/search",
            headers=student_headers,
            params={"query": unique, "school": "西安电子科技大学"},
        )
        answer = client.post(
            "/api/v1/chat/answer",
            headers=student_headers,
            json={
                "content": f"请解答资料编号 {unique} 中的采样问题",
                "target_school": "西安电子科技大学",
            },
        )

    assert unauthorized.status_code == 401
    assert created.status_code == 201
    assert "西安电子科技大学" in schools.json()
    assert search.status_code == 200
    assert search.json()[0]["id"] == created.json()["id"]
    assert answer.status_code == 200
    assert answer.json()["sources"][0]["entry_id"] == created.json()["id"]


def test_admin_imports_text_file_and_can_unpublish_entry() -> None:
    unique = uuid4().hex[:8]
    with TestClient(app) as client:
        imported = client.post(
            "/api/v1/admin/knowledge/import",
            headers=ADMIN_HEADERS,
            data={
                "title": f"傅里叶公式表 {unique}",
                "kind": "formula",
                "chapter": "fourier_transform",
                "topics": "傅里叶变换,对偶性质",
            },
            files={"file": ("formula.txt", f"{unique}\n\n傅里叶变换具有对偶性质。", "text/plain")},
        )
        entry_id = imported.json()["entries"][0]["id"]
        unpublished = client.patch(
            f"/api/v1/admin/knowledge/{entry_id}",
            headers=ADMIN_HEADERS,
            json={"published": False},
        )
        student_headers, _ = create_authenticated_headers(client, username_prefix="knowledge-file")
        search = client.get(
            "/api/v1/knowledge/search",
            headers=student_headers,
            params={"query": unique},
        )

    assert imported.status_code == 200
    assert imported.json()["imported"] == 1
    assert unpublished.status_code == 200
    assert unpublished.json()["published"] is False
    assert all(item["id"] != entry_id for item in search.json())
