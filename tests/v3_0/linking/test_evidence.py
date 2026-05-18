"""Tests for gallodoc.linking.evidence — evidence builder."""

from __future__ import annotations

from gallodoc.linking.evidence import SIGNAL_TO_EVIDENCE_TYPE, build_evidence
from gallodoc.linking.scoring import ScoredCandidate, Signal


def _scored_with(*signals: Signal) -> ScoredCandidate:
    sc = ScoredCandidate(source_document_id="doc_a", candidate_document_id="doc_b")
    for s in signals:
        sc.add_signal(s)
    return sc


def test_each_signal_produces_evidence_entry_with_expected_type() -> None:
    h = "sha256:" + "a" * 64
    cases = [
        ("text_hash_match", "shared_text_hash", h),
        ("claim_id_match", "shared_claim_id", None),
        ("projection_hash_match", "shared_projection_hash", h),
        ("shared_evidence_ref", "shared_evidence_ref", None),
        ("semantic_intent_match", "semantic_intent_match", None),
        ("source_record_id_match", "shared_source_record_id", h),
        ("relationship_evidence_match", "shared_relationship_value_hash", h),
        ("semantic_role_overlap", "shared_semantic_role", None),
    ]
    for signal_name, expected_type, value_hash in cases:
        sig = Signal(
            name=signal_name,
            weight=0.5,
            source_locator=f"<{signal_name}-source>",
            candidate_locator=f"<{signal_name}-candidate>",
            match_value_hash=value_hash,
        )
        scored = _scored_with(sig)
        entries = build_evidence(scored)
        assert len(entries) == 1
        entry = entries[0]
        assert entry["evidence_type"] == expected_type
        assert entry["weight"] == 0.5
        assert entry["source_locator"] == f"<{signal_name}-source>"
        assert entry["candidate_locator"] == f"<{signal_name}-candidate>"
        if value_hash is not None:
            assert entry["value_hash"] == value_hash
        else:
            assert "value_hash" not in entry


def test_value_hash_only_appears_when_signal_has_one() -> None:
    sig_no_hash = Signal(
        name="claim_id_match",
        weight=0.85,
        source_locator="truth_ledger.claims[claim_id=c1]",
        candidate_locator="truth_ledger.claims[claim_id=c1]",
        match_value_hash=None,
    )
    scored = _scored_with(sig_no_hash)
    entry = build_evidence(scored)[0]
    assert "value_hash" not in entry


def test_no_raw_text_in_evidence_entries() -> None:
    """Evidence entries carry only hashes, IDs, and short vocabulary tokens.

    Build a candidate from an envelope-like input and verify that no raw
    text/PHI snippets leak into the emitted entries.
    """
    sigs = [
        Signal(
            name="text_hash_match",
            weight=0.95,
            source_locator="gallounits.units[unit_id=u1].text_hash",
            candidate_locator="gallounits.units[unit_id=u2].text_hash",
            match_value_hash="sha256:" + "a" * 64,
        ),
        Signal(
            name="semantic_intent_match",
            weight=0.60,
            source_locator="gallounits.units[].semantic_intent=invoice_to_employee_approver",
            candidate_locator="gallounits.units[].semantic_intent=invoice_to_employee_approver",
            match_value_hash=None,
        ),
    ]
    scored = _scored_with(*sigs)
    entries = build_evidence(scored)
    for entry in entries:
        for key, value in entry.items():
            if not isinstance(value, str):
                continue
            # No "name:" patterns or pseudo-PHI strings
            assert "patient name" not in value.lower()
            assert "ssn" not in value.lower()


def test_unknown_signal_name_passes_through() -> None:
    sig = Signal(
        name="unknown_signal_x",
        weight=0.0,
        source_locator="src",
        candidate_locator="cand",
    )
    entries = build_evidence(_scored_with(sig))
    assert entries[0]["evidence_type"] == "unknown_signal_x"


def test_signal_to_evidence_type_covers_all_known_signals() -> None:
    """Every signal name produced by scoring.extract_signals has a mapping."""
    expected = {
        "text_hash_match", "claim_id_match", "projection_hash_match",
        "shared_evidence_ref", "semantic_intent_match",
        "source_record_id_match", "relationship_evidence_match",
        "semantic_role_overlap",
    }
    assert set(SIGNAL_TO_EVIDENCE_TYPE) == expected
