"""Tests for the per-model projection helpers."""

from __future__ import annotations

from gallodoc.units import build_gallounits_block
from gallodoc.units.projections import (
    build_model_projection,
    estimate_tokens_for_unit,
    register_token_estimator,
)


def test_estimator_falls_back_to_char_count():
    unit = {"unit_id": "gu_001", "content_summary": "Net 30 payment terms apply."}
    n = estimate_tokens_for_unit(unit, provider="custom", model="custom-001")
    assert n >= 1
    # ~4 chars per token rule
    assert n <= len(unit["content_summary"])


def test_build_model_projection_shape():
    units = build_gallounits_block("Net 30 payment terms apply.\n\nThe provider shall deliver.")
    projections = build_model_projection(units["units"], provider="openai", model="gpt-4o")
    assert len(projections) == len(units["units"])
    for p in projections:
        assert p["provider"] == "openai"
        assert p["model"] == "gpt-4o"
        assert p["projection_hash"].startswith("sha256:")
        assert p["token_count"] >= 0


def test_projections_are_per_unit_and_pointback_to_unit_id():
    units = build_gallounits_block("Net 30 payment terms apply.\n\nThe provider shall deliver.")
    projections = build_model_projection(units["units"], provider="anthropic", model="claude-opus-4-7")
    unit_ids = {u["unit_id"] for u in units["units"]}
    assert {p["unit_id"] for p in projections} == unit_ids


def test_register_custom_estimator_overrides_default():
    register_token_estimator("custom", "magic", lambda t, p, m: 999)
    n = estimate_tokens_for_unit({"content_summary": "hi"}, provider="custom", model="magic")
    assert n == 999


def test_projection_never_pretends_tokens_are_universal():
    units = build_gallounits_block("Net 30 payment terms apply.")
    a = build_model_projection(units["units"], provider="openai", model="gpt-4o", tokenizer="o200k_base")
    b = build_model_projection(units["units"], provider="anthropic", model="claude-opus-4-7", tokenizer="anthropic_v2")
    # Same unit, different tokenizer → different projection_hash.
    assert a[0]["projection_hash"] != b[0]["projection_hash"]
    assert a[0]["unit_id"] == b[0]["unit_id"]
