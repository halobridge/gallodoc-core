"""Tests for gallodoc.linking.rules — relationship type catalog."""

from __future__ import annotations

import pytest

from gallodoc.linking.rules import (
    ALLOWED_RELATIONSHIP_TYPES,
    SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE,
    classify,
)
from gallodoc.linking.scoring import ScoredCandidate, Signal


def _scored(*sig_names: str, intent: str | None = None) -> ScoredCandidate:
    """Build a scored candidate with the named signals (and optional intent)."""
    scored = ScoredCandidate(source_document_id="doc_a", candidate_document_id="doc_b")
    for name in sig_names:
        if name == "semantic_intent_match" and intent:
            scored.add_signal(Signal(
                name=name,
                weight=0.60,
                source_locator=f"gallounits.units[].semantic_intent={intent}",
                candidate_locator=f"gallounits.units[].semantic_intent={intent}",
            ))
        else:
            scored.add_signal(Signal(
                name=name,
                weight=0.5,
                source_locator=f"<{name}-source>",
                candidate_locator=f"<{name}-candidate>",
            ))
    return scored


@pytest.mark.parametrize(
    "intent,expected_type,expected_reason",
    [
        ("invoice_to_employee_approver", "related_to", "invoice_to_employee_approver"),
        ("contract_supersedes_contract", "supersedes", "contract_supersedes_contract"),
        ("patient_to_consent_record", "belongs_to", "patient_to_consent_record"),
        ("claim_to_supporting_document", "supports", "claim_to_supporting_document"),
        ("case_to_case_continuation", "derived_from", "case_to_case_continuation"),
        ("attachment_to_parent_document", "belongs_to", "attachment_to_parent_document"),
    ],
)
def test_known_semantic_intent_maps_to_expected_type(intent: str, expected_type: str, expected_reason: str) -> None:
    scored = _scored("semantic_intent_match", intent=intent)
    rel_type, reason = classify(scored)
    assert rel_type == expected_type
    assert reason == expected_reason


def test_unknown_semantic_intent_defaults_to_related_to_with_intent_as_reason() -> None:
    scored = _scored("semantic_intent_match", intent="something_not_in_vocabulary")
    rel_type, reason = classify(scored)
    assert rel_type == "related_to"
    assert reason == "something_not_in_vocabulary"


def test_semantic_intent_wins_over_other_signals() -> None:
    """When intent fires alongside other signals, intent wins."""
    scored = _scored(
        "text_hash_match",
        "claim_id_match",
        "semantic_intent_match",
        intent="invoice_to_employee_approver",
    )
    rel_type, reason = classify(scored)
    assert rel_type == "related_to"
    assert reason == "invoice_to_employee_approver"


def test_claim_id_match_yields_same_claim() -> None:
    scored = _scored("claim_id_match")
    rel_type, reason = classify(scored)
    assert rel_type == "same_claim"
    assert reason == "shared_canonical_claim"


def test_text_hash_match_yields_duplicate_of() -> None:
    scored = _scored("text_hash_match")
    rel_type, reason = classify(scored)
    assert rel_type == "duplicate_of"
    assert reason == "shared_canonical_text"


def test_source_record_id_match_yields_duplicate_of() -> None:
    scored = _scored("source_record_id_match")
    rel_type, reason = classify(scored)
    assert rel_type == "duplicate_of"
    assert reason == "shared_source_record_id"


def test_projection_hash_match_yields_derived_from() -> None:
    scored = _scored("projection_hash_match")
    rel_type, reason = classify(scored)
    assert rel_type == "derived_from"
    assert reason == "shared_tokenization_stable_content"


def test_default_with_no_signals_yields_related_to() -> None:
    scored = _scored()
    rel_type, reason = classify(scored)
    assert rel_type == "related_to"
    assert reason is None


def test_default_with_only_role_overlap_yields_related_to() -> None:
    scored = _scored("semantic_role_overlap")
    rel_type, reason = classify(scored)
    assert rel_type == "related_to"
    assert reason is None


def test_classify_priority_claim_id_over_text_hash() -> None:
    """When claim_id and text_hash both fire (no intent), claim_id wins."""
    scored = _scored("claim_id_match", "text_hash_match")
    rel_type, _ = classify(scored)
    assert rel_type == "same_claim"


def test_classify_priority_text_hash_over_projection_hash() -> None:
    scored = _scored("text_hash_match", "projection_hash_match")
    rel_type, _ = classify(scored)
    assert rel_type == "duplicate_of"


def test_all_emitted_types_are_in_allowed_set() -> None:
    """Every (signal_name → relationship_type) mapping in this module must
    produce a value that the v2.0 validator accepts."""
    # Each known intent maps inside the allowed set.
    for intent, (rel_type, _reason) in SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE.items():
        assert rel_type in ALLOWED_RELATIONSHIP_TYPES, (
            f"intent {intent!r} → {rel_type!r} not in allowed enum"
        )
    # Signal-pattern paths
    for sig in ["claim_id_match", "text_hash_match", "source_record_id_match",
                "projection_hash_match", "semantic_role_overlap", "shared_evidence_ref"]:
        scored = _scored(sig)
        rel_type, _ = classify(scored)
        assert rel_type in ALLOWED_RELATIONSHIP_TYPES, (
            f"signal {sig!r} → {rel_type!r} not in allowed enum"
        )
    # Default
    rel_type, _ = classify(_scored())
    assert rel_type in ALLOWED_RELATIONSHIP_TYPES


def test_allowed_relationship_types_matches_validator_set() -> None:
    """ALLOWED_RELATIONSHIP_TYPES tracks the v2.0 enum in the validator."""
    expected = {
        "duplicate_of", "version_of", "supersedes", "belongs_to", "supports",
        "contradicts", "same_claim", "same_patient", "same_customer",
        "same_contract", "same_invoice", "derived_from", "related_to",
    }
    assert ALLOWED_RELATIONSHIP_TYPES == expected
