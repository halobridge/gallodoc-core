"""Tests for ``gallodoc.training.safety`` — privacy scan over pairs."""

from __future__ import annotations

import pytest

from gallodoc.projection.safety import EnterpriseLeakageError
from gallodoc.training.pairs import TrainingPair, _make_pair_id
from gallodoc.training.safety import assert_pairs_clean


def _clean_pair(i: int = 0) -> TrainingPair:
    source = f"doc_src_{i}"
    target = f"doc_tgt_{i}"
    return TrainingPair(
        pair_id=_make_pair_id(source, target, "related_to", "match"),
        source_gallodoc_ref=source,
        target_gallodoc_ref=target,
        relationship_type="related_to",
        semantic_intent=None,
        label="match",
        evidence_refs=["ev_clean"],
        reviewer_decision=None,
        confidence=0.5,
        discovered_by="human",
        created_at="2026-05-16T00:00:00Z",
    )


def test_clean_pairs_pass_safety_scan() -> None:
    pairs = [_clean_pair(i) for i in range(5)]
    assert_pairs_clean(pairs)  # no raise


def test_empty_pair_list_passes() -> None:
    assert_pairs_clean([])  # no raise


def test_policy_formula_in_evidence_ref_is_blocked() -> None:
    """A 'policy_formula'-shaped *key* triggers the platform-internal-key check.

    The scan walks the dict tree and rejects any key in
    {"policy_formula", "halobridge_internal", "__internal__"} no matter
    where it appears. We seed it through evidence_refs by injecting it
    via a custom subclass that overrides to_dict.
    """
    class _LeakyPair(TrainingPair):
        def to_dict(self):  # type: ignore[override]
            d = super().to_dict()
            d["policy_formula"] = "x = a + b"  # forbidden key name
            return d

    pair = _LeakyPair(
        pair_id="pair_leak0000000000",
        source_gallodoc_ref="a",
        target_gallodoc_ref="b",
        relationship_type="related_to",
        semantic_intent=None,
        label="match",
        evidence_refs=[],
        reviewer_decision=None,
        confidence=0.0,
        discovered_by="human",
        created_at="2026-05-16T00:00:00Z",
    )
    with pytest.raises(EnterpriseLeakageError):
        assert_pairs_clean([pair])


def test_ssn_like_string_in_discovered_by_is_blocked() -> None:
    """Synthetic SSN-shaped string would never appear in real envelopes."""
    pair = _clean_pair()
    pair.discovered_by = "leak from 123-45-6789"
    with pytest.raises(EnterpriseLeakageError, match="SSN-like"):
        assert_pairs_clean([pair])


def test_error_message_identifies_offending_pair_index() -> None:
    good_a = _clean_pair(0)
    good_b = _clean_pair(1)
    bad = _clean_pair(2)
    bad.discovered_by = "leak 123-45-6789"
    with pytest.raises(EnterpriseLeakageError) as exc_info:
        assert_pairs_clean([good_a, good_b, bad])
    msg = str(exc_info.value)
    assert "training pair 2" in msg
    assert bad.pair_id in msg
