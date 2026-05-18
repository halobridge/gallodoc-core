"""GalloUnit-keyed deterministic linker orchestration.

Per Decision 3 (output writes into ``relationships`` with
``status: "suggested"`` and ``discovered_by: "gallodoc-linker/3.0.0"``)
and Decision 5 (``::semantic_intent`` carries author-asserted intent
across envelopes).

The linker's ``relationship_id`` is a deterministic function of
``(source_document_id, target_document_id, relationship_type)`` so
re-runs on the same input produce the same IDs and consumers can de-dup.
``apply_relationship_decision`` is the only supported path to flip a
linker-suggested entry to ``confirmed`` / ``rejected``; it preserves
``discovered_by`` and appends a ``relationship_decisions[]`` record.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from gallodoc.linking.evidence import build_evidence
from gallodoc.linking.rules import classify
from gallodoc.linking.scoring import ScoredCandidate, score


LINKER_DISCOVERED_BY: str = "gallodoc-linker/3.0.0"


@dataclass
class RelationshipCandidate:
    """A relationship the linker proposes between two envelopes."""

    relationship_id: str
    source_document_id: str
    target_document_id: str
    relationship_type: str
    reason_code: str | None
    status: str
    discovered_by: str
    confidence: float
    relationship_evidence: list[dict[str, Any]] = field(default_factory=list)
    semantic_intent: str | None = None  # Decision 5: carry matched intent
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "relationship_id": self.relationship_id,
            "source_document_ref": self.source_document_id,
            "target_document_ref": self.target_document_id,
            "relationship_type": self.relationship_type,
            "status": self.status,
            "discovered_by": self.discovered_by,
            "confidence": self.confidence,
            "relationship_evidence": self.relationship_evidence,
            "created_at": self.created_at,
        }
        if self.reason_code is not None:
            out["reason_code"] = self.reason_code
        if self.semantic_intent is not None:
            out["semantic_intent"] = self.semantic_intent
        return out


@dataclass
class LinkerOutput:
    """Result of a linker run."""

    source_document_id: str
    candidates: list[RelationshipCandidate] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _make_relationship_id(source_id: str, target_id: str, rel_type: str) -> str:
    """Deterministic relationship_id derived from (source, target, type)."""
    payload = f"{source_id}::{target_id}::{rel_type}".encode("utf-8")
    return "rel_" + hashlib.sha256(payload).hexdigest()[:16]


def _extract_semantic_intent(scored: ScoredCandidate) -> str | None:
    for sig in scored.signals:
        if sig.name == "semantic_intent_match":
            return sig.source_locator.split("semantic_intent=", 1)[-1]
    return None


def link(
    source_envelope: dict[str, Any],
    candidate_envelopes: Iterable[dict[str, Any]],
    min_confidence: float = 0.10,
) -> LinkerOutput:
    """Run the linker on a source envelope and a set of candidates.

    Returns a :class:`LinkerOutput` with relationship candidates, all
    ``status: "suggested"`` and
    ``discovered_by: "gallodoc-linker/3.0.0"``. Candidates below
    ``min_confidence`` are dropped. A candidate equal to the source
    (same ``gallodoc_id``) is skipped.
    """
    src_id = (source_envelope.get("identity") or {}).get("gallodoc_id") or "(unknown_source)"
    out = LinkerOutput(source_document_id=src_id)
    now = _now_iso()

    for cand_env in candidate_envelopes:
        cand_id = (cand_env.get("identity") or {}).get("gallodoc_id") or "(unknown_candidate)"
        if cand_id == src_id:
            continue  # don't link an envelope to itself

        scored = score(source_envelope, cand_env)
        if scored.confidence < min_confidence:
            continue

        rel_type, reason_code = classify(scored, source_envelope, cand_env)
        rel_id = _make_relationship_id(src_id, cand_id, rel_type)
        evidence = build_evidence(scored)
        intent = _extract_semantic_intent(scored)

        out.candidates.append(RelationshipCandidate(
            relationship_id=rel_id,
            source_document_id=src_id,
            target_document_id=cand_id,
            relationship_type=rel_type,
            reason_code=reason_code,
            status="suggested",                  # Decision 3 — pinned
            discovered_by=LINKER_DISCOVERED_BY,  # Decision 3 — pinned
            confidence=scored.confidence,
            relationship_evidence=evidence,
            semantic_intent=intent,
            created_at=now,
        ))

    return out


def write_into_envelope(envelope: dict[str, Any], output: LinkerOutput) -> dict[str, Any]:
    """Append linker output to ``envelope.relationships.relationships[]``.

    Returns the modified envelope. Preserves existing entries — linker
    appends, never overwrites. If a ``relationship_id`` collides
    (idempotent re-run), the new entry replaces the old one in place.
    """
    rel_block = envelope.get("relationships")
    if not isinstance(rel_block, dict):
        # v3 shape: relationships is an object containing relationships[].
        # Coerce any legacy bare-array shape (or absence) to the v3 shape.
        rel_block = {
            "relationships": rel_block if isinstance(rel_block, list) else [],
        }
        envelope["relationships"] = rel_block

    entries = rel_block.setdefault("relationships", [])
    existing_ids: dict[str, int] = {}
    for i, e in enumerate(entries):
        if isinstance(e, dict) and e.get("relationship_id"):
            existing_ids[e["relationship_id"]] = i

    for c in output.candidates:
        new_entry = c.to_dict()
        if c.relationship_id in existing_ids:
            # Idempotent: replace in place
            entries[existing_ids[c.relationship_id]] = new_entry
        else:
            existing_ids[c.relationship_id] = len(entries)
            entries.append(new_entry)

    return envelope


def apply_relationship_decision(
    envelope: dict[str, Any],
    relationship_id: str,
    verdict: str,
    decided_by: str,
    rationale: str | None = None,
) -> dict[str, Any]:
    """Flip a linker-suggested relationship to confirmed or rejected.

    Decision 3 lifecycle: preserves ``discovered_by`` so the audit trail
    shows machine proposed + human confirmed. Appends a record to
    ``relationship_decisions[]``. Idempotent: re-applying the same
    verdict on an already-decided entry is a no-op.

    Raises :class:`ValueError` if ``verdict`` is not in
    ``{"confirmed", "rejected"}`` or if ``relationship_id`` is not found.
    """
    if verdict not in {"confirmed", "rejected"}:
        raise ValueError(
            f"verdict must be 'confirmed' or 'rejected', got {verdict!r}"
        )

    rel_block = envelope.get("relationships")
    if not isinstance(rel_block, dict):
        raise ValueError("envelope.relationships is not an object")
    entries = rel_block.get("relationships") or []
    target: dict[str, Any] | None = None
    for e in entries:
        if isinstance(e, dict) and e.get("relationship_id") == relationship_id:
            target = e
            break
    if target is None:
        raise ValueError(f"relationship_id {relationship_id!r} not found")

    if target.get("status") == verdict:
        return envelope  # idempotent — no-op

    target["status"] = verdict

    decisions = rel_block.setdefault("relationship_decisions", [])
    decided_at = _now_iso()
    payload = f"{relationship_id}::{verdict}::{decided_by}::{decided_at}"
    decision_id = "dec_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    decisions.append({
        "decision_id": decision_id,
        "relationship_id": relationship_id,
        "verdict": verdict,
        "decided_by": decided_by,
        "decided_at": decided_at,
        "rationale": rationale or "",
    })

    return envelope


__all__ = [
    "LINKER_DISCOVERED_BY",
    "LinkerOutput",
    "RelationshipCandidate",
    "apply_relationship_decision",
    "link",
    "write_into_envelope",
]
