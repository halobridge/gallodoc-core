"""Tests for ``gallodoc.training.exporter`` — pair extraction from envelopes."""

from __future__ import annotations

import copy
from typing import Any

from gallodoc.training import (
    TrainingPair,
    extract_pairs_from_envelope,
    extract_pairs_from_envelopes,
)


def _rel(
    rid: str,
    *,
    status: str,
    discovered_by: str = "human_review",
    source_ref: str = "doc_a",
    target_ref: str = "doc_b",
    rel_type: str = "related_to",
    confidence: float = 0.9,
    semantic_intent: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "relationship_id": rid,
        "source_document_ref": source_ref,
        "target_document_ref": target_ref,
        "relationship_type": rel_type,
        "status": status,
        "discovered_by": discovered_by,
        "confidence": confidence,
    }
    if semantic_intent is not None:
        entry["semantic_intent"] = semantic_intent
    return entry


def _decision(
    rid: str,
    *,
    verdict: str,
    decided_by: str = "ap_lead@example.com",
    decided_at: str = "2026-05-16T12:00:00Z",
) -> dict[str, Any]:
    return {
        "decision_id": f"dec_{rid}",
        "relationship_id": rid,
        "verdict": verdict,
        "decided_by": decided_by,
        "decided_at": decided_at,
    }


def _evidence(rid: str, eid: str) -> dict[str, Any]:
    return {
        "evidence_id": eid,
        "relationship_id": rid,
        "evidence_type": "field_match",
        "field_name": "vendor_name",
        "value_hash": "sha256:0" * 8,
    }


def _envelope_with(
    relationships: list[dict[str, Any]],
    decisions: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "gallodoc-core/v3",
        "relationships": {
            "schema_version": "gallodoc.relationships.v3.0",
            "relationships": relationships,
            "relationship_decisions": decisions or [],
            "relationship_evidence": evidence or [],
        },
    }


def test_confirmed_with_decision_becomes_match() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="confirmed")],
        [_decision("rel_1", verdict="confirmed")],
    )
    pairs = extract_pairs_from_envelope(env)
    assert len(pairs) == 1
    assert pairs[0].label == "match"
    assert pairs[0].reviewer_decision is not None
    assert pairs[0].reviewer_decision["verdict"] == "confirmed"


def test_rejected_with_decision_becomes_non_match() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="rejected")],
        [_decision("rel_1", verdict="rejected")],
    )
    pairs = extract_pairs_from_envelope(env)
    assert len(pairs) == 1
    assert pairs[0].label == "non_match"
    assert pairs[0].reviewer_decision is not None
    assert pairs[0].reviewer_decision["verdict"] == "rejected"


def test_suggested_no_decision_becomes_uncertain() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="suggested", discovered_by="gallodoc-linker/3.0.0")],
        [],
    )
    pairs = extract_pairs_from_envelope(env)
    assert len(pairs) == 1
    assert pairs[0].label == "uncertain"
    assert pairs[0].reviewer_decision is None


def test_linker_discovered_plus_confirmed_is_positive() -> None:
    """Decision 3: linker-confirmed pairs are the highest-quality positives."""
    env = _envelope_with(
        [_rel("rel_1", status="confirmed", discovered_by="gallodoc-linker/3.0.0")],
        [_decision("rel_1", verdict="confirmed")],
    )
    pairs = extract_pairs_from_envelope(env)
    assert len(pairs) == 1
    p = pairs[0]
    assert p.label == "match"
    assert p.discovered_by == "gallodoc-linker/3.0.0"  # carried through verbatim
    assert p.reviewer_decision is not None


def test_confirmed_without_decision_record_is_skipped() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="confirmed")],
        [],  # missing decision record
    )
    assert extract_pairs_from_envelope(env) == []


def test_rejected_without_decision_record_is_skipped() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="rejected")],
        [],  # missing decision record
    )
    assert extract_pairs_from_envelope(env) == []


def test_suggested_with_decision_record_is_skipped() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="suggested")],
        [_decision("rel_1", verdict="confirmed")],  # inconsistent
    )
    assert extract_pairs_from_envelope(env) == []


def test_invalid_status_is_skipped() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="rumoured")],
        [],
    )
    assert extract_pairs_from_envelope(env) == []


def test_empty_envelope_returns_empty_list() -> None:
    env = {"schema_version": "gallodoc-core/v3"}
    assert extract_pairs_from_envelope(env) == []


def test_pair_id_is_deterministic_across_runs() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="confirmed")],
        [_decision("rel_1", verdict="confirmed")],
    )
    a = extract_pairs_from_envelope(copy.deepcopy(env))
    b = extract_pairs_from_envelope(copy.deepcopy(env))
    assert a[0].pair_id == b[0].pair_id


def test_evidence_refs_are_carried_through() -> None:
    env = _envelope_with(
        [_rel("rel_1", status="confirmed")],
        [_decision("rel_1", verdict="confirmed")],
        [_evidence("rel_1", "ev_alpha"), _evidence("rel_1", "ev_beta")],
    )
    pairs = extract_pairs_from_envelope(env)
    assert len(pairs) == 1
    assert pairs[0].evidence_refs == ["ev_alpha", "ev_beta"]


def test_semantic_intent_is_carried_through() -> None:
    env = _envelope_with(
        [
            _rel(
                "rel_1",
                status="confirmed",
                semantic_intent="invoice_to_employee_approver",
            )
        ],
        [_decision("rel_1", verdict="confirmed")],
    )
    pairs = extract_pairs_from_envelope(env)
    assert len(pairs) == 1
    assert pairs[0].semantic_intent == "invoice_to_employee_approver"


def test_multi_envelope_convenience() -> None:
    env_a = _envelope_with(
        [_rel("rel_a", status="confirmed", source_ref="doc_x", target_ref="doc_y")],
        [_decision("rel_a", verdict="confirmed")],
    )
    env_b = _envelope_with(
        [_rel("rel_b", status="rejected", source_ref="doc_m", target_ref="doc_n")],
        [_decision("rel_b", verdict="rejected")],
    )
    pairs = extract_pairs_from_envelopes([env_a, env_b])
    assert len(pairs) == 2
    assert {p.label for p in pairs} == {"match", "non_match"}


def test_output_pairs_are_well_formed() -> None:
    """Smoke-check: required fields are non-None where the spec demands."""
    env = _envelope_with(
        [_rel("rel_1", status="confirmed")],
        [_decision("rel_1", verdict="confirmed")],
    )
    pairs = extract_pairs_from_envelope(env)
    for p in pairs:
        assert isinstance(p, TrainingPair)
        assert p.pair_id and p.pair_id.startswith("pair_")
        assert p.source_gallodoc_ref
        assert p.target_gallodoc_ref
        assert p.relationship_type
        assert p.label in {"match", "non_match", "uncertain"}
        assert isinstance(p.evidence_refs, list)
        assert isinstance(p.confidence, float)
        assert p.created_at.endswith("Z")
