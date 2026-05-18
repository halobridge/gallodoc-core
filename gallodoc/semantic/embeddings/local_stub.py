"""Local stub embedding adapter — deterministic, no external dependencies.

Used as the default adapter in tests and in environments without an
installed embedding model. The "embedding" is a hash-derived float
vector with stable dimensions (32). Same input → same vector.

This adapter is intentionally NOT a real embedding model — the vectors
are cryptographic noise, not semantic embeddings. Use it for:

- Round-trip and integration tests.
- CI runs that need a deterministic embedding without downloading model
  weights.
- Smoke-testing the ``gallodoc semantic embed`` CLI surface.

Never call this for production retrieval.
"""

from __future__ import annotations

import hashlib
import struct

from gallodoc.semantic.embeddings.base import EmbeddingAdapter


class LocalStubEmbeddingAdapter(EmbeddingAdapter):
    """Deterministic hash-derived adapter.

    No external dependencies — works on stdlib only. ``available()``
    always returns ``True``. ``embed([])`` returns ``[]``.
    """

    slug = "local_stub"
    version = "3.0.0"
    model_id = "gallodoc.embedder.local_stub.v3.0"
    dimensions = 32

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        if not text:
            # Empty string → all-zeros vector (documented contract).
            return [0.0] * self.dimensions
        # Derive a deterministic vector from SHA-256(text).
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # SHA-256 yields 32 bytes; we need 32 floats × 4 bytes = 128 bytes.
        # Repeat the digest as needed so the buffer is long enough.
        n_bytes_needed = self.dimensions * 4
        repeats = (n_bytes_needed // len(digest)) + 1
        buf = (digest * repeats)[:n_bytes_needed]
        floats = struct.unpack(f"{self.dimensions}f", buf)
        # Normalize so values are in [-1.0, 1.0]. Dividing by the
        # maximum absolute value gives stable, comparable output across
        # texts (different texts still produce different vectors because
        # the raw float bit-patterns differ).
        max_abs = max(abs(f) for f in floats) or 1.0
        return [float(f) / max_abs for f in floats]


__all__ = ["LocalStubEmbeddingAdapter"]
