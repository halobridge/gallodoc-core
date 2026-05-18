"""Tests for the GalloDoc Units engine."""

from __future__ import annotations

from gallodoc.units import (
    UNIT_STRATEGY_V1,
    build_gallounits_block,
    compute_text_hash,
    normalize_text,
    segment_text_to_units,
)


SAMPLE_TEXT = """\
MASTER SERVICES AGREEMENT

This agreement is entered into by Acme Corp (synthetic) and Synthetic LLC.

Net 30 payment terms apply to all invoices. The provider shall deliver
the work product within 14 days.

The parties hereby agree to the terms set forth above.

Signature: ______________________
"""


def test_normalize_text_is_deterministic():
    a = normalize_text("  hello   world\r\nfoo  ")
    b = normalize_text("hello world\nfoo")
    assert a == b == "hello world\nfoo"


def test_text_hash_is_stable_across_whitespace_variants():
    h1 = compute_text_hash("Net 30 payment terms apply.")
    h2 = compute_text_hash("  Net   30   payment   terms   apply.  ")
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_segment_text_to_units_returns_ordered_units():
    units = segment_text_to_units(SAMPLE_TEXT)
    assert len(units) >= 4
    assert all(u["unit_id"].startswith("gu_") for u in units)
    # offsets are monotonic
    last_end = -1
    for u in units:
        assert u["source_span"]["start_char"] >= last_end
        last_end = u["source_span"]["end_char"]


def test_segment_classifies_payment_terms_and_signature():
    units = segment_text_to_units(SAMPLE_TEXT)
    types = {u["unit_type"] for u in units}
    assert "payment_terms" in types
    assert "signature_block" in types


def test_build_gallounits_block_shape_matches_schema():
    block = build_gallounits_block(SAMPLE_TEXT)
    assert block["unit_strategy"] == UNIT_STRATEGY_V1
    assert block["canonical_text_hash"].startswith("sha256:")
    assert isinstance(block["units"], list)
    assert isinstance(block["model_projections"], list)


def test_segment_with_unknown_strategy_raises():
    import pytest as _pytest

    with _pytest.raises(ValueError):
        segment_text_to_units("hello", strategy="unknown_strategy")


def test_unit_ids_are_unique_within_a_doc():
    units = segment_text_to_units(SAMPLE_TEXT)
    assert len({u["unit_id"] for u in units}) == len(units)


def test_empty_text_returns_no_units():
    assert segment_text_to_units("") == []
    assert build_gallounits_block("")["units"] == []
