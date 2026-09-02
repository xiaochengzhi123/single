from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredAsset:
    key: str
    sha256: str
    mime_type: str
    size_bytes: int
    width: int
    height: int


class Storage(Protocol):
    async def save_image(self, data: bytes, claimed_mime: str | None = None) -> StoredAsset: ...
    async def read(self, key: str) -> bytes: ...
