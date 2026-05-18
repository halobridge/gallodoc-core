"""Tests for ``gallodoc.training.pairs`` — schema + helpers."""

from __future__ import annotations

from gallodoc.training.pairs import LABEL_ENUM, TrainingPair, _make_pair_id


def _make_pair(**overrides) -> TrainingPair:
    base = dict(
        pair_id="pair_0000000000000000",
        source_gallodoc_ref="doc_a",
        target_gallodoc_ref="doc_b",
        relationship_type="related_to",
        semantic_intent=None,
        label="match",
        evidence_refs=[],
        reviewer_decision=None,
        confidence=0.5,
        discovered_by="human",
        created_at="2026-05-16T00:00:00Z",
    )
    base.update(overrides)
    return TrainingPair(**base)


def test_to_dict_has_eleven_documented_keys() -> None:
    pair = _make_pair()
    out = pair.to_dict()
    assert set(out.keys()) == {
        "pair_id",
        "source_gallodoc_ref",
        "target_gallodoc_ref",
        "relationship_type",
        "semantic_intent",
        "label",
        "evidence_refs",
        "reviewer_decision",
        "confidence",
        "discovered_by",
        "created_at",
    }
    assert len(out) == 11


def test_to_dict_round_trips_fields_verbatim() -> None:
    pair = _make_pair(
        semantic_intent="invoice_to_employee_approver",
        label="non_match",
        evidence_refs=["ev_1", "ev_2"],
        reviewer_decision={"decision_id": "dec_x"},
        confidence=0.9,
        discovered_by="gallodoc-linker/3.0.0",
    )
    out = pair.to_dict()
    assert out["semantic_intent"] == "invoice_to_employee_approver"
    assert out["label"] == "non_match"
    assert out["evidence_refs"] == ["ev_1", "ev_2"]
    assert out["reviewer_decision"] == {"decision_id": "dec_x"}
    assert out["confidence"] == 0.9
    assert out["discovered_by"] == "gallodoc-linker/3.0.0"


def test_label_enum_has_exactly_three_entries() -> None:
    assert LABEL_ENUM == frozenset({"match", "non_match", "uncertain"})
    assert len(LABEL_ENUM) == 3


def test_make_pair_id_is_deterministic_for_same_inputs() -> None:
    a1 = _make_pair_id("doc_a", "doc_b", "related_to", "match")
    a2 = _make_pair_id("doc_a", "doc_b", "related_to", "match")
    assert a1 == a2


def test_make_pair_id_differs_for_different_inputs() -> None:
    base = _make_pair_id("doc_a", "doc_b", "related_to", "match")
    diff_source = _make_pair_id("doc_x", "doc_b", "related_to", "match")
    diff_target = _make_pair_id("doc_a", "doc_x", "related_to", "match")
    diff_type = _make_pair_id("doc_a", "doc_b", "same_customer", "match")
    diff_label = _make_pair_id("doc_a", "doc_b", "related_to", "non_match")
    assert len({base, diff_source, diff_target, diff_type, diff_label}) == 5


def test_make_pair_id_starts_with_prefix_and_is_correct_length() -> None:
    pid = _make_pair_id("a", "b", "c", "match")
    assert pid.startswith("pair_")
    # "pair_" (5) + 16 hex chars = 21 total
    assert len(pid) == 21
