import io

import pytest
from PIL import Image

from signaltutor.storage.local import ImageValidationError, validate_and_normalize_image


def test_valid_png_is_detected_from_bytes() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), "white").save(buffer, "PNG")
    data, extension, mime, width, height = validate_and_normalize_image(buffer.getvalue(), 100_000)
    assert data
    assert (extension, mime, width, height) == (".png", "image/png", 32, 24)


def test_fake_image_is_rejected() -> None:
    with pytest.raises(ImageValidationError):
        validate_and_normalize_image(b"not an image", 100_000)


def test_oversized_image_is_rejected_before_decode() -> None:
    with pytest.raises(ImageValidationError, match="超过"):
        validate_and_normalize_image(b"x" * 101, 100)
