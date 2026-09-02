import io

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.main import app
from tests.conftest import create_authenticated_headers


def test_low_confidence_image_requires_confirmation_without_key() -> None:
    image = io.BytesIO()
    Image.new("RGB", (80, 50), "white").save(image, "PNG")
    with TestClient(app) as client:
        headers, _ = create_authenticated_headers(client)
        response = client.post(
            "/api/v1/problems/upload",
            headers=headers,
            files={"file": ("problem.png", image.getvalue(), "image/png")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_confirmation"
    assert body["problem_parse"]["uncertain_elements"]
