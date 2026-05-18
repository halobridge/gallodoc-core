"""Build relationship_evidence[] arrays from scored signals.

Each linker signal becomes a relationship_evidence entry carrying only
hashes, weights, and opaque locator strings — never raw text or PHI.
"""

from __future__ import annotations

from typing import Any

from gallodoc.linking.scoring import ScoredCandidate


# Mapping signal name → relationship_evidence.evidence_type tag. Keeps the
# emitted ``evidence_type`` values human-readable for audit while reusing
# the canonical signal names from the scoring module.
SIGNAL_TO_EVIDENCE_TYPE: dict[str, str] = {
    "text_hash_match":             "shared_text_hash",
    "claim_id_match":              "shared_claim_id",
    "projection_hash_match":       "shared_projection_hash",
    "shared_evidence_ref":         "shared_evidence_ref",
    "semantic_intent_match":       "semantic_intent_match",
    "source_record_id_match":     "shared_source_record_id",
    "relationship_evidence_match": "shared_relationship_value_hash",
    "semantic_role_overlap":       "shared_semantic_role",
}


def build_evidence(scored: ScoredCandidate) -> list[dict[str, Any]]:
    """Turn signals into a relationship_evidence[] array.

    Hashes and locators only; no raw text or PHI.
    """
    out: list[dict[str, Any]] = []
    for sig in scored.signals:
        entry: dict[str, Any] = {
            "evidence_type": SIGNAL_TO_EVIDENCE_TYPE.get(sig.name, sig.name),
            "weight": sig.weight,
            "source_locator": sig.source_locator,
            "candidate_locator": sig.candidate_locator,
        }
        if sig.match_value_hash:
            entry["value_hash"] = sig.match_value_hash
        out.append(entry)
    return out


__all__ = ["SIGNAL_TO_EVIDENCE_TYPE", "build_evidence"]
