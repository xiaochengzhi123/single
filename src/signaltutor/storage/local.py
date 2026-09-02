from __future__ import annotations

import asyncio
import hashlib
import io
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from signaltutor.storage.base import StoredAsset

ALLOWED_FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}


class ImageValidationError(ValueError):
    pass


def validate_and_normalize_image(data: bytes, max_bytes: int) -> tuple[bytes, str, str, int, int]:
    if not data:
        raise ImageValidationError("图片为空")
    if len(data) > max_bytes:
        raise ImageValidationError(f"图片超过 {max_bytes} 字节限制")
    try:
        with Image.open(io.BytesIO(data)) as opened:
            opened.verify()
        with Image.open(io.BytesIO(data)) as opened:
            image = ImageOps.exif_transpose(opened)
            fmt = opened.format or ""
            if fmt not in ALLOWED_FORMATS:
                raise ImageValidationError("仅支持 JPEG、PNG、WEBP")
            if image.width * image.height > 40_000_000:
                raise ImageValidationError("图片像素数量过大")
            image.thumbnail((4096, 4096))
            extension, mime = ALLOWED_FORMATS[fmt]
            output = io.BytesIO()
            save_format = "JPEG" if fmt == "JPEG" else fmt
            converted = image.convert("RGB") if save_format == "JPEG" else image
            converted.save(output, format=save_format, optimize=True)
            return output.getvalue(), extension, mime, converted.width, converted.height
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageValidationError("文件不是可解码的图片") from exc


class LocalStorage:
    def __init__(self, root: Path, max_bytes: int) -> None:
        self.root = root
        self.max_bytes = max_bytes

    async def save_image(self, data: bytes, claimed_mime: str | None = None) -> StoredAsset:
        normalized, extension, mime, width, height = await asyncio.to_thread(
            validate_and_normalize_image, data, self.max_bytes
        )
        if claimed_mime and claimed_mime not in {mime, "application/octet-stream"}:
            raise ImageValidationError("声明的 MIME 与实际图片格式不一致")
        digest = hashlib.sha256(normalized).hexdigest()
        self.root.mkdir(parents=True, exist_ok=True)
        key = f"{uuid4()}{extension}"
        path = self.root / key
        await asyncio.to_thread(path.write_bytes, normalized)
        return StoredAsset(key, digest, mime, len(normalized), width, height)

    async def read(self, key: str) -> bytes:
        if Path(key).name != key:
            raise ImageValidationError("非法 storage key")
        return await asyncio.to_thread((self.root / key).read_bytes)
