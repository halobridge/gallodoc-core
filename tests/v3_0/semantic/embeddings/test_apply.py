"""Tests for ``apply_embeddings`` — the envelope-integration entry point."""

from __future__ import annotations

import copy

import pytest

from gallodoc.projection.safety import EnterpriseLeakageError
from gallodoc.semantic.embeddings import (
    LocalStubEmbeddingAdapter,
    apply_embeddings,
)
from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


_REQUIRED_EMBEDDING_KEYS = {
    "embedding_id",
    "unit_id",
    "model_id",
    "model_hash_or_id",
    "dimensions",
    "vector_ref",
    "embedding_hash",
    "purpose",
    "created_at",
}


def _envelope_with_units(*, raw_vectors_stored: bool = False) -> dict:
    env = minimal_v3_envelope()
    env["gallounits"]["units"] = [
        {
            "unit_id": "gu_001",
            "unit_type": "sentence",
            "text_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "content_summary": "Vendor invoice total is $1,234.56.",
        },
        {
            "unit_id": "gu_002",
            "unit_type": "sentence",
            "text_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "content_summary": "Approver: jane.doe@example.com.",
        },
    ]
    if raw_vectors_stored:
        env["safety_profile"] = {"raw_vectors_stored": True}
    return env


def test_appends_one_embedding_per_unit_with_content_summary():
    env = _envelope_with_units()
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    embeddings = out["gallounits"]["embeddings"]
    assert len(embeddings) == 2


def test_each_embedding_has_all_required_fields():
    env = _envelope_with_units()
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    for rec in out["gallounits"]["embeddings"]:
        assert _REQUIRED_EMBEDDING_KEYS <= set(rec)


def test_embedding_purpose_matches_input():
    env = _envelope_with_units()
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "entity_context_embedding")
    for rec in out["gallounits"]["embeddings"]:
        assert rec["purpose"] == "entity_context_embedding"


def test_embedding_unit_id_resolves_to_a_unit():
    env = _envelope_with_units()
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    known_unit_ids = {u["unit_id"] for u in out["gallounits"]["units"]}
    for rec in out["gallounits"]["embeddings"]:
        assert rec["unit_id"] in known_unit_ids


def test_raw_vector_not_in_output_by_default():
    env = _envelope_with_units()
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    for rec in out["gallounits"]["embeddings"]:
        assert "raw_vector" not in rec


def test_include_vector_without_safety_profile_raises():
    env = _envelope_with_units(raw_vectors_stored=False)
    with pytest.raises(EnterpriseLeakageError) as exc_info:
        apply_embeddings(
            env,
            LocalStubEmbeddingAdapter(),
            "document_summary_embedding",
            include_vector=True,
        )
    assert "raw_vectors_stored" in str(exc_info.value)


def test_include_vector_with_safety_profile_populates_raw_vector():
    env = _envelope_with_units(raw_vectors_stored=True)
    out = apply_embeddings(
        env,
        LocalStubEmbeddingAdapter(),
        "document_summary_embedding",
        include_vector=True,
    )
    for rec in out["gallounits"]["embeddings"]:
        assert "raw_vector" in rec
        assert len(rec["raw_vector"]) == rec["dimensions"]


def test_idempotent_no_duplicate_embeddings():
    env = _envelope_with_units()
    out1 = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    first_ids = sorted(r["embedding_id"] for r in out1["gallounits"]["embeddings"])
    out2 = apply_embeddings(out1, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    second_ids = sorted(r["embedding_id"] for r in out2["gallounits"]["embeddings"])
    assert first_ids == second_ids
    assert len(out2["gallounits"]["embeddings"]) == 2


def test_different_purposes_produce_different_embedding_ids():
    env = _envelope_with_units()
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    out = apply_embeddings(out, LocalStubEmbeddingAdapter(), "entity_context_embedding")
    # Two purposes × two units = four embeddings.
    assert len(out["gallounits"]["embeddings"]) == 4
    ids = {r["embedding_id"] for r in out["gallounits"]["embeddings"]}
    assert len(ids) == 4


def test_invalid_purpose_raises_value_error():
    env = _envelope_with_units()
    with pytest.raises(ValueError):
        apply_embeddings(env, LocalStubEmbeddingAdapter(), "not_a_real_purpose")


def test_units_without_content_summary_are_skipped():
    env = _envelope_with_units()
    env["gallounits"]["units"].append(
        {
            "unit_id": "gu_003",
            "unit_type": "sentence",
            "text_hash": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            # No content_summary — must be skipped.
        }
    )
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    embedded_unit_ids = {r["unit_id"] for r in out["gallounits"]["embeddings"]}
    assert "gu_003" not in embedded_unit_ids
    assert len(out["gallounits"]["embeddings"]) == 2


def test_output_envelope_passes_validate_envelope():
    env = _envelope_with_units()
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    result = validate_envelope(out)
    assert result.valid, f"validation failed: {[i.message for i in result.issues]}"


def test_embedding_id_is_deterministic():
    env1 = _envelope_with_units()
    env2 = _envelope_with_units()
    out1 = apply_embeddings(env1, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    out2 = apply_embeddings(env2, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    ids1 = sorted(r["embedding_id"] for r in out1["gallounits"]["embeddings"])
    ids2 = sorted(r["embedding_id"] for r in out2["gallounits"]["embeddings"])
    assert ids1 == ids2


def test_embedding_hash_is_deterministic():
    env1 = _envelope_with_units()
    env2 = _envelope_with_units()
    out1 = apply_embeddings(env1, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    out2 = apply_embeddings(env2, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    hashes1 = sorted(r["embedding_hash"] for r in out1["gallounits"]["embeddings"])
    hashes2 = sorted(r["embedding_hash"] for r in out2["gallounits"]["embeddings"])
    assert hashes1 == hashes2


def test_vector_ref_uses_embedding_id():
    env = _envelope_with_units()
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    for rec in out["gallounits"]["embeddings"]:
        assert rec["vector_ref"] == f"opaque://store/{rec['embedding_id']}"


def test_empty_envelope_units_produces_empty_embeddings():
    env = minimal_v3_envelope()
    # No units at all.
    out = apply_embeddings(env, LocalStubEmbeddingAdapter(), "document_summary_embedding")
    assert out["gallounits"].get("embeddings", []) == []
