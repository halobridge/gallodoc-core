"""Tests for the deterministic train/dev/test splitter."""

from __future__ import annotations

import copy

import pytest

from gallodoc.training.pairs import TrainingPair, _make_pair_id
from gallodoc.training.splitter import split_train_dev_test


def _make_pair(i: int) -> TrainingPair:
    source = f"doc_src_{i}"
    target = f"doc_tgt_{i}"
    rel_type = "related_to"
    label = "match"
    return TrainingPair(
        pair_id=_make_pair_id(source, target, rel_type, label),
        source_gallodoc_ref=source,
        target_gallodoc_ref=target,
        relationship_type=rel_type,
        semantic_intent=None,
        label=label,
        evidence_refs=[],
        reviewer_decision=None,
        confidence=1.0,
        discovered_by="human",
        created_at="2026-05-16T00:00:00Z",
    )


def test_default_80_10_10_split_is_close_to_target() -> None:
    pairs = [_make_pair(i) for i in range(1000)]
    out = split_train_dev_test(pairs)
    assert sum(len(v) for v in out.values()) == 1000
    # Stochastic; tolerate ±10% on each bucket.
    assert 700 <= len(out["train"]) <= 900
    assert 50 <= len(out["dev"]) <= 150
    assert 50 <= len(out["test"]) <= 150


def test_same_input_and_seed_produces_identical_partition() -> None:
    pairs = [_make_pair(i) for i in range(200)]
    a = split_train_dev_test(copy.deepcopy(pairs))
    b = split_train_dev_test(copy.deepcopy(pairs))
    assert [p.pair_id for p in a["train"]] == [p.pair_id for p in b["train"]]
    assert [p.pair_id for p in a["dev"]] == [p.pair_id for p in b["dev"]]
    assert [p.pair_id for p in a["test"]] == [p.pair_id for p in b["test"]]


def test_different_seed_changes_partition() -> None:
    pairs = [_make_pair(i) for i in range(200)]
    a = split_train_dev_test(pairs, seed=42)
    b = split_train_dev_test(pairs, seed=43)
    # The partition should differ on at least one pair (probability of
    # equality on 200 independent buckets is effectively zero).
    a_train_ids = {p.pair_id for p in a["train"]}
    b_train_ids = {p.pair_id for p in b["train"]}
    assert a_train_ids != b_train_ids


def test_empty_input_returns_three_empty_lists() -> None:
    out = split_train_dev_test([])
    assert out == {"train": [], "dev": [], "test": []}


def test_ratios_not_summing_to_one_raises_value_error() -> None:
    with pytest.raises(ValueError, match="must sum to 1.0"):
        split_train_dev_test([], ratios=(0.7, 0.1, 0.1))


def test_negative_ratio_raises_value_error() -> None:
    with pytest.raises(ValueError, match="must be non-negative"):
        split_train_dev_test([], ratios=(1.2, -0.1, -0.1))


def test_pair_lands_in_same_split_regardless_of_input_order() -> None:
    """Determinism guarantee: a pair_id's bucket is order-independent."""
    pairs = [_make_pair(i) for i in range(50)]
    forward = split_train_dev_test(list(pairs))
    reverse = split_train_dev_test(list(reversed(pairs)))
    # Build pair_id → split-name maps and compare set membership.
    def membership(out: dict[str, list[TrainingPair]]) -> dict[str, str]:
        return {p.pair_id: split for split, lst in out.items() for p in lst}

    assert membership(forward) == membership(reverse)
