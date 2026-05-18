"""Tests for gallodoc.linking.scoring — signal extraction + confidence."""

from __future__ import annotations

import pytest

from gallodoc.linking.scoring import (
    SHARED_EVIDENCE_REF_CAP,
    SIGNAL_WEIGHTS,
    ScoredCandidate,
    Signal,
    extract_signals,
    score,
)


def _envelope(identity: str, **sections: dict) -> dict:
    """Build a minimal source envelope with the named sections populated."""
    env: dict = {
        "identity": {"gallodoc_id": identity},
        "gallounits": {"units": [], "model_projections": []},
        "truth_ledger": {"claims": []},
        "source": {},
        "relationships": {"relationships": [], "relationship_evidence": []},
    }
    for key, val in sections.items():
        env[key] = val
    return env


def test_no_signals_yields_zero_confidence() -> None:
    src = _envelope("doc_a")
    cand = _envelope("doc_b")
    scored = score(src, cand)
    assert scored.signals == []
    assert scored.confidence == 0.0


def test_text_hash_match_extracts_signal() -> None:
    h = "sha256:" + "a" * 64
    src = _envelope(
        "doc_a",
        gallounits={"units": [{"unit_id": "u1", "text_hash": h}]},
    )
    cand = _envelope(
        "doc_b",
        gallounits={"units": [{"unit_id": "u2", "text_hash": h}]},
    )
    sigs = extract_signals(src, cand)
    names = [s.name for s in sigs]
    assert names == ["text_hash_match"]
    sig = sigs[0]
    assert sig.weight == SIGNAL_WEIGHTS["text_hash_match"]
    assert sig.weight == 0.95
    assert sig.match_value_hash == h
    assert "u1" in sig.source_locator
    assert "u2" in sig.candidate_locator


def test_text_hash_only_confidence_is_0_95() -> None:
    h = "sha256:" + "a" * 64
    src = _envelope("doc_a", gallounits={"units": [{"unit_id": "u1", "text_hash": h}]})
    cand = _envelope("doc_b", gallounits={"units": [{"unit_id": "u2", "text_hash": h}]})
    scored = score(src, cand)
    assert scored.confidence == 0.95


def test_claim_id_match_extracts_signal() -> None:
    src = _envelope(
        "doc_a",
        truth_ledger={"claims": [{"claim_id": "claim:abc"}]},
    )
    cand = _envelope(
        "doc_b",
        truth_ledger={"claims": [{"claim_id": "claim:abc"}]},
    )
    sigs = extract_signals(src, cand)
    assert [s.name for s in sigs] == ["claim_id_match"]
    assert sigs[0].weight == 0.85
    assert "claim:abc" in sigs[0].source_locator


def test_projection_hash_match_extracts_signal() -> None:
    h = "sha256:" + "b" * 64
    src = _envelope(
        "doc_a",
        gallounits={
            "units": [],
            "model_projections": [{"projection_id": "p1", "projection_hash": h}],
        },
    )
    cand = _envelope(
        "doc_b",
        gallounits={
            "units": [],
            "model_projections": [{"projection_id": "p2", "projection_hash": h}],
        },
    )
    sigs = extract_signals(src, cand)
    assert [s.name for s in sigs] == ["projection_hash_match"]
    assert sigs[0].weight == 0.70
    assert sigs[0].match_value_hash == h


def test_shared_evidence_ref_extracts_one_signal_per_ref() -> None:
    src = _envelope(
        "doc_a",
        truth_ledger={
            "claims": [
                {"claim_id": "c1", "evidence_refs": ["ev:1", "ev:2"]},
            ]
        },
    )
    cand = _envelope(
        "doc_b",
        truth_ledger={
            "claims": [
                {"claim_id": "c2", "evidence_refs": ["ev:1", "ev:2"]},
            ]
        },
    )
    sigs = extract_signals(src, cand)
    names = [s.name for s in sigs]
    # 2 shared refs
    assert names.count("shared_evidence_ref") == 2
    assert all(s.weight == 0.60 for s in sigs)


def test_semantic_intent_match_extracts_signal() -> None:
    src = _envelope(
        "doc_a",
        gallounits={
            "units": [{"unit_id": "u1", "semantic_intent": "invoice_to_employee_approver"}],
        },
    )
    cand = _envelope(
        "doc_b",
        gallounits={
            "units": [{"unit_id": "u2", "semantic_intent": "invoice_to_employee_approver"}],
        },
    )
    sigs = extract_signals(src, cand)
    assert [s.name for s in sigs] == ["semantic_intent_match"]
    assert sigs[0].weight == 0.60
    assert "invoice_to_employee_approver" in sigs[0].source_locator


def test_source_record_id_match_extracts_signal() -> None:
    rid = "sha256:" + "c" * 64
    src = _envelope("doc_a", source={"source_record_id_hash": rid})
    cand = _envelope("doc_b", source={"source_record_id_hash": rid})
    sigs = extract_signals(src, cand)
    assert [s.name for s in sigs] == ["source_record_id_match"]
    assert sigs[0].weight == 0.50
    assert sigs[0].match_value_hash == rid


def test_relationship_evidence_value_hash_match_extracts_signal() -> None:
    h = "sha256:" + "d" * 64
    src = _envelope(
        "doc_a",
        relationships={
            "relationships": [],
            "relationship_evidence": [{"evidence_id": "ev_a", "value_hash": h}],
        },
    )
    cand = _envelope(
        "doc_b",
        relationships={
            "relationships": [],
            "relationship_evidence": [{"evidence_id": "ev_b", "value_hash": h}],
        },
    )
    sigs = extract_signals(src, cand)
    assert [s.name for s in sigs] == ["relationship_evidence_match"]
    assert sigs[0].weight == 0.40
    assert sigs[0].match_value_hash == h


def test_semantic_role_overlap_extracts_signal_at_low_weight() -> None:
    src = _envelope(
        "doc_a",
        gallounits={"units": [{"unit_id": "u1", "semantic_role": "approver"}]},
    )
    cand = _envelope(
        "doc_b",
        gallounits={"units": [{"unit_id": "u2", "semantic_role": "approver"}]},
    )
    sigs = extract_signals(src, cand)
    assert [s.name for s in sigs] == ["semantic_role_overlap"]
    assert sigs[0].weight == 0.10


def test_shared_evidence_ref_cap_limits_confidence_contributions() -> None:
    # 5 shared refs — but only SHARED_EVIDENCE_REF_CAP (3) contribute.
    src = _envelope(
        "doc_a",
        truth_ledger={
            "claims": [
                {"claim_id": "c1", "evidence_refs": [f"ev:{i}" for i in range(5)]},
            ]
        },
    )
    cand = _envelope(
        "doc_b",
        truth_ledger={
            "claims": [
                {"claim_id": "c2", "evidence_refs": [f"ev:{i}" for i in range(5)]},
            ]
        },
    )
    scored = score(src, cand)
    # All 5 captured for audit, but confidence caps at 3 * 0.6 = 1.8 → clamped to 1.0.
    assert sum(1 for s in scored.signals if s.name == "shared_evidence_ref") == 5
    # 3 * 0.6 = 1.8 → clamp to 1.0
    assert scored.confidence == 1.0


def test_shared_evidence_ref_cap_with_two_refs_does_not_overcontribute() -> None:
    # 2 shared refs → confidence = 2 * 0.6 = 1.2 → clamped to 1.0.
    src = _envelope(
        "doc_a",
        truth_ledger={"claims": [{"claim_id": "c1", "evidence_refs": ["ev:1", "ev:2"]}]},
    )
    cand = _envelope(
        "doc_b",
        truth_ledger={"claims": [{"claim_id": "c2", "evidence_refs": ["ev:1", "ev:2"]}]},
    )
    scored = score(src, cand)
    assert scored.confidence == 1.0


def test_confidence_clamps_at_one() -> None:
    # Stack multiple strong signals — should clamp at 1.0.
    h = "sha256:" + "a" * 64
    src = _envelope(
        "doc_a",
        gallounits={"units": [{"unit_id": "u1", "text_hash": h, "semantic_intent": "invoice_to_employee_approver"}]},
        truth_ledger={"claims": [{"claim_id": "c1"}]},
    )
    cand = _envelope(
        "doc_b",
        gallounits={"units": [{"unit_id": "u2", "text_hash": h, "semantic_intent": "invoice_to_employee_approver"}]},
        truth_ledger={"claims": [{"claim_id": "c1"}]},
    )
    scored = score(src, cand)
    # 0.95 + 0.85 + 0.60 = 2.40 → clamped to 1.0
    assert scored.confidence == 1.0


def test_single_low_weight_signal_does_not_overcount() -> None:
    src = _envelope(
        "doc_a",
        gallounits={"units": [{"unit_id": "u1", "semantic_role": "approver"}]},
    )
    cand = _envelope(
        "doc_b",
        gallounits={"units": [{"unit_id": "u2", "semantic_role": "approver"}]},
    )
    scored = score(src, cand)
    assert scored.confidence == 0.10


def test_no_raw_text_in_signal_outputs() -> None:
    """Signals carry only hashes, IDs, and short vocabulary tokens — never raw text."""
    # synthetic "raw-text-shaped" string; intentionally not a real-looking
    # identifier (release safety scan flags realistic SSN/PAN patterns).
    raw = "patient narrative text not for export"
    src = _envelope(
        "doc_a",
        gallounits={"units": [{"unit_id": "u1", "content_summary": raw, "text_hash": "sha256:" + "e" * 64}]},
    )
    cand = _envelope(
        "doc_b",
        gallounits={"units": [{"unit_id": "u2", "content_summary": raw, "text_hash": "sha256:" + "e" * 64}]},
    )
    sigs = extract_signals(src, cand)
    for s in sigs:
        assert raw not in s.source_locator
        assert raw not in s.candidate_locator
        assert s.match_value_hash != raw


def test_score_returns_scored_candidate_with_ids() -> None:
    src = _envelope("doc_a")
    cand = _envelope("doc_b")
    scored = score(src, cand)
    assert isinstance(scored, ScoredCandidate)
    assert scored.source_document_id == "doc_a"
    assert scored.candidate_document_id == "doc_b"


def test_unknown_ids_fall_back_to_placeholder() -> None:
    src = {"gallounits": {"units": []}}
    cand = {"gallounits": {"units": []}}
    scored = score(src, cand)
    assert scored.source_document_id == "(unknown_source)"
    assert scored.candidate_document_id == "(unknown_candidate)"
