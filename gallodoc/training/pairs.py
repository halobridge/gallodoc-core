"""Training pair schema + helpers.

The :class:`TrainingPair` dataclass is the canonical exported shape.
See ``docs/specs/gallodoc-core-v3-training-lab.md`` §2.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


LABEL_ENUM: frozenset[str] = frozenset({"match", "non_match", "uncertain"})


@dataclass
class TrainingPair:
    """A single training pair exported from a v3 envelope.

    Attributes
    ----------
    pair_id:
        ``"pair_" + sha256(f"{source_ref}::{target_ref}::{rel_type}::{label}")[:16]``.
        Deterministic — same inputs always produce the same ID.
    source_gallodoc_ref / target_gallodoc_ref:
        Opaque envelope refs (no document content).
    relationship_type:
        v2.0 enum value carried through from the source relationship.
    semantic_intent:
        Decision 5 vocabulary value (or ``None``).
    label:
        Closed enum: ``match`` / ``non_match`` / ``uncertain``.
    evidence_refs:
        ``evidence_id`` strings from ``relationship_evidence[]``.
    reviewer_decision:
        The matching ``relationship_decisions[]`` record verbatim, or
        ``None`` for uncertain / hard-negative pairs.
    confidence:
        Confidence on the source relationship, or ``0.0`` for synthetic
        negatives.
    discovered_by:
        Carried through verbatim. Synthetic negatives use
        ``"hard_negative:<strategy>"``.
    created_at:
        ISO 8601 UTC timestamp at which the pair was emitted.
    """

    pair_id: str
    source_gallodoc_ref: str
    target_gallodoc_ref: str
    relationship_type: str
    semantic_intent: str | None
    label: str
    evidence_refs: list[str]
    reviewer_decision: dict[str, Any] | None
    confidence: float
    discovered_by: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Return the 11-key dict shape documented in the spec."""
        return {
            "pair_id": self.pair_id,
            "source_gallodoc_ref": self.source_gallodoc_ref,
            "target_gallodoc_ref": self.target_gallodoc_ref,
            "relationship_type": self.relationship_type,
            "semantic_intent": self.semantic_intent,
            "label": self.label,
            "evidence_refs": self.evidence_refs,
            "reviewer_decision": self.reviewer_decision,
            "confidence": self.confidence,
            "discovered_by": self.discovered_by,
            "created_at": self.created_at,
        }


def _now_iso() -> str:
    """ISO 8601 UTC timestamp, second precision, ``Z`` suffix."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _make_pair_id(source_ref: str, target_ref: str, rel_type: str, label: str) -> str:
    """Deterministic ``pair_id`` derived from (source, target, type, label)."""
    payload = f"{source_ref}::{target_ref}::{rel_type}::{label}".encode("utf-8")
    return "pair_" + hashlib.sha256(payload).hexdigest()[:16]


__all__ = ["TrainingPair", "LABEL_ENUM"]
