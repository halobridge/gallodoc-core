"""Open embeddings adapter interface.

This module defines the contract every embedding adapter implements:
the ``EmbeddingAdapter`` ABC, the ``EmbeddingRecord`` storage shape,
the closed ``PURPOSE_ENUM``, and the small set of helpers used by
``apply_embeddings`` (now-iso clock, deterministic vector hashing,
purpose validation).

See ``docs/specs/gallodoc-core-v3-embeddings.md`` for the full spec.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


PURPOSE_ENUM: frozenset[str] = frozenset({
    "document_summary_embedding",
    "relationship_embedding",
    "entity_context_embedding",
    "workflow_context_embedding",
    "risk_context_embedding",
    "policy_context_embedding",
})


@dataclass
class EmbeddingRecord:
    """A single embedding entry in ``gallounits.embeddings[]``.

    The default storage shape ships only metadata + a deterministic
    hash + an opaque ref. The raw vector floats are excluded from
    ``to_dict()`` unless they have been explicitly populated and the
    caller has cleared the ``--include-vector`` safety gate.
    """

    embedding_id: str
    unit_id: str
    model_id: str
    model_hash_or_id: str
    dimensions: int
    vector_ref: str           # opaque ref, e.g. "opaque://store/<id>"
    embedding_hash: str        # SHA-256 of the vector (deterministic)
    purpose: str               # must be in PURPOSE_ENUM
    created_at: str            # ISO-8601 RFC 3339 UTC
    raw_vector: list[float] | None = None
    """Populated only when ``--include-vector`` is set AND
    ``safety_profile.raw_vectors_stored`` is true on the envelope."""

    def to_dict(self) -> dict[str, Any]:
        """Render as a dict suitable for ``gallounits.embeddings[]``.

        Omits ``raw_vector`` unless it has been explicitly populated.
        Keys are emitted in the canonical order documented in the
        spec (`embedding_id`, `unit_id`, `model_id`, …).
        """
        out: dict[str, Any] = {
            "embedding_id": self.embedding_id,
            "unit_id": self.unit_id,
            "model_id": self.model_id,
            "model_hash_or_id": self.model_hash_or_id,
            "dimensions": self.dimensions,
            "vector_ref": self.vector_ref,
            "embedding_hash": self.embedding_hash,
            "purpose": self.purpose,
            "created_at": self.created_at,
        }
        if self.raw_vector is not None:
            out["raw_vector"] = self.raw_vector
        return out


class EmbeddingAdapter(ABC):
    """Open embeddings adapter contract.

    Subclasses override:
      - ``slug`` — stable adapter identifier (e.g. ``"local_stub"``).
      - ``version`` — adapter version (semver).
      - ``model_id`` — opaque model identifier the adapter uses.
      - ``dimensions`` — embedding dimensions.
      - ``embed(texts)`` — the single hot-path method.
      - ``available()`` (optional) — class method indicating whether
        the adapter's optional dependencies are importable.
    """

    slug: str = ""
    version: str = ""
    model_id: str = ""
    dimensions: int = 0

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text.

        Implementations must never raise on empty input
        (``embed([])`` must return ``[]``). Callers use this to probe
        the adapter without loading a model.
        """

    @classmethod
    def available(cls) -> bool:
        """True iff the adapter's optional dependencies are importable.

        Adapters that need extras (``bge_m3``, ``sentence_transformers``)
        override this so the CLI can decide whether to surface them in
        ``--help`` / error messages without paying the lazy-import cost.
        The base default is ``True`` — adapters with no extras
        (``local_stub``) inherit this.
        """
        return True


def now_iso() -> str:
    """Return current UTC time as ISO-8601 ending in ``Z``.

    Same convention as ``gallodoc.connectors.base.now_iso``. We strip
    ``+00:00`` so the string is short and matches the RFC 3339 ``Z``
    convention used elsewhere in the envelope.
    """
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def hash_vector(vector: list[float]) -> str:
    """Deterministic SHA-256 of a vector's canonical serialization.

    Each float is rendered with ``f"{v:.6f}"`` and joined by commas.
    Same input vector → same hash. The fixed-precision format means
    floats that are equal to 6 decimals hash identically — adequate
    for detecting drift; not adequate for cryptographic identity of
    the underlying weights, which is handled elsewhere via
    ``model_hash_or_id``.
    """
    canonical = ",".join(f"{v:.6f}" for v in vector)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_purpose(purpose: str) -> None:
    """Raise ``ValueError`` if ``purpose`` is not in ``PURPOSE_ENUM``."""
    if purpose not in PURPOSE_ENUM:
        raise ValueError(
            f"purpose must be one of {sorted(PURPOSE_ENUM)}, got {purpose!r}"
        )


__all__ = [
    "EmbeddingAdapter",
    "EmbeddingRecord",
    "PURPOSE_ENUM",
    "now_iso",
    "hash_vector",
    "validate_purpose",
]
