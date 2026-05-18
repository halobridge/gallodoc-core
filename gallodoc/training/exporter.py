"""Extract training pairs from v3 envelopes.

Reads ``envelope.relationships.relationships[]`` and
``envelope.relationships.relationship_decisions[]`` and emits one
:class:`TrainingPair` per valid entry.

Pair sources (see ``docs/specs/gallodoc-core-v3-training-lab.md`` §3):

  * ``status == "confirmed"`` AND matching decision   → ``label: "match"``
  * ``status == "rejected"``  AND matching decision   → ``label: "non_match"``
  * ``status == "suggested"`` AND NO matching decision → ``label: "uncertain"``

Any other combination is an inconsistent state and is skipped (the v3
validator catches these). Per Decision 3, linker-discovered +
human-confirmed entries are **included** as positives — they are the
highest-quality supervision signal.
"""

from __future__ import annotations

from typing import Any, Iterable

from gallodoc.training.pairs import TrainingPair, _make_pair_id, _now_iso


_VALID_STATUSES: frozenset[str] = frozenset({"suggested", "confirmed", "rejected"})


def _decision_index(rel_block: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map ``relationship_id`` → decision record."""
    decisions = rel_block.get("relationship_decisions") or []
    index: dict[str, dict[str, Any]] = {}
    for d in decisions:
        if not isinstance(d, dict):
            continue
        rid = d.get("relationship_id")
        if isinstance(rid, str) and rid:
            index[rid] = d
    return index


def _evidence_index(rel_block: dict[str, Any]) -> dict[str, list[str]]:
    """Map ``relationship_id`` → list of evidence_id strings."""
    items = rel_block.get("relationship_evidence") or []
    out: dict[str, list[str]] = {}
    for e in items:
        if not isinstance(e, dict):
            continue
        rid = e.get("relationship_id")
        eid = e.get("evidence_id")
        if isinstance(rid, str) and isinstance(eid, str) and rid and eid:
            out.setdefault(rid, []).append(eid)
    return out


def extract_pairs_from_envelope(envelope: dict[str, Any]) -> list[TrainingPair]:
    """Extract training pairs from a single v3 envelope.

    Returns a list (possibly empty). Entries violating the Decision 3
    status / decision-record lifecycle are silently skipped — they would
    have been caught by the v3 validator before reaching this stage.
    """
    rel_block = envelope.get("relationships")
    if not isinstance(rel_block, dict):
        return []

    entries = rel_block.get("relationships") or []
    if not isinstance(entries, list):
        return []

    decisions_by_rid = _decision_index(rel_block)
    evidence_by_rid = _evidence_index(rel_block)
    now = _now_iso()

    pairs: list[TrainingPair] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        rid = entry.get("relationship_id")
        if not isinstance(rid, str) or not rid:
            continue

        status = entry.get("status")
        if status not in _VALID_STATUSES:
            continue  # bad status — skip

        decision = decisions_by_rid.get(rid)

        # Determine the label from status + decision-record presence.
        if status == "confirmed":
            if decision is None:
                continue  # inconsistent: confirmed without decision record
            label = "match"
            reviewer_decision = decision
        elif status == "rejected":
            if decision is None:
                continue  # inconsistent: rejected without decision record
            label = "non_match"
            reviewer_decision = decision
        else:  # status == "suggested"
            if decision is not None:
                continue  # inconsistent: suggested with decision record
            label = "uncertain"
            reviewer_decision = None

        source_ref = entry.get("source_document_ref")
        target_ref = entry.get("target_document_ref")
        rel_type = entry.get("relationship_type")
        if not (
            isinstance(source_ref, str)
            and isinstance(target_ref, str)
            and isinstance(rel_type, str)
        ):
            continue  # malformed entry

        confidence_raw = entry.get("confidence", 0.0)
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0

        discovered_by = entry.get("discovered_by") or ""
        if not isinstance(discovered_by, str):
            discovered_by = ""

        semantic_intent = entry.get("semantic_intent")
        if not isinstance(semantic_intent, str):
            semantic_intent = None

        evidence_refs = list(evidence_by_rid.get(rid, []))

        pair = TrainingPair(
            pair_id=_make_pair_id(source_ref, target_ref, rel_type, label),
            source_gallodoc_ref=source_ref,
            target_gallodoc_ref=target_ref,
            relationship_type=rel_type,
            semantic_intent=semantic_intent,
            label=label,
            evidence_refs=evidence_refs,
            reviewer_decision=reviewer_decision,
            confidence=confidence,
            discovered_by=discovered_by,
            created_at=now,
        )
        pairs.append(pair)

    return pairs


def extract_pairs_from_envelopes(
    envelopes: Iterable[dict[str, Any]],
) -> list[TrainingPair]:
    """Multi-envelope convenience wrapper."""
    out: list[TrainingPair] = []
    for env in envelopes:
        out.extend(extract_pairs_from_envelope(env))
    return out


__all__ = ["extract_pairs_from_envelope", "extract_pairs_from_envelopes"]
