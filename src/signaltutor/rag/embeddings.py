from __future__ import annotations

import hashlib
import math


def deterministic_embedding(text: str, dimensions: int = 64) -> list[float]:
    """Offline test embedding; production ingestion may replace it with Qwen embeddings."""
    vector = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        vector[int.from_bytes(digest[:2], "big") % dimensions] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
