"""Tests for the embeddings adapter base interface."""

from __future__ import annotations

import pytest

from gallodoc.semantic.embeddings.base import (
    EmbeddingRecord,
    PURPOSE_ENUM,
    hash_vector,
    now_iso,
    validate_purpose,
)


def test_purpose_enum_has_six_entries():
    assert len(PURPOSE_ENUM) == 6


def test_purpose_enum_canonical_values():
    expected = {
        "document_summary_embedding",
        "relationship_embedding",
        "entity_context_embedding",
        "workflow_context_embedding",
        "risk_context_embedding",
        "policy_context_embedding",
    }
    assert set(PURPOSE_ENUM) == expected


def test_validate_purpose_accepts_each_known_purpose():
    for purpose in PURPOSE_ENUM:
        # Must not raise.
        validate_purpose(purpose)


def test_validate_purpose_rejects_unknown():
    with pytest.raises(ValueError) as exc_info:
        validate_purpose("not_a_real_purpose")
    msg = str(exc_info.value)
    # Error should list the closed enum so callers can fix themselves.
    assert "not_a_real_purpose" in msg
    for purpose in PURPOSE_ENUM:
        assert purpose in msg


def test_hash_vector_deterministic():
    v = [0.1, -0.2, 0.3]
    h1 = hash_vector(v)
    h2 = hash_vector(v)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_hash_vector_differs_on_different_input():
    h1 = hash_vector([0.1, 0.2, 0.3])
    h2 = hash_vector([0.1, 0.2, 0.4])
    assert h1 != h2


def test_now_iso_ends_with_z():
    stamp = now_iso()
    assert stamp.endswith("Z")
    # Looks like an ISO 8601 timestamp.
    assert "T" in stamp


def test_embedding_record_to_dict_documented_keys():
    rec = EmbeddingRecord(
        embedding_id="emb_0001",
        unit_id="gu_001",
        model_id="m",
        model_hash_or_id="sha256:abc",
        dimensions=4,
        vector_ref="opaque://store/emb_0001",
        embedding_hash="sha256:def",
        purpose="document_summary_embedding",
        created_at="2026-05-16T00:00:00Z",
    )
    d = rec.to_dict()
    assert set(d) == {
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


def test_embedding_record_to_dict_omits_raw_vector_by_default():
    rec = EmbeddingRecord(
        embedding_id="emb_0001",
        unit_id="gu_001",
        model_id="m",
        model_hash_or_id="sha256:abc",
        dimensions=4,
        vector_ref="opaque://store/emb_0001",
        embedding_hash="sha256:def",
        purpose="document_summary_embedding",
        created_at="2026-05-16T00:00:00Z",
    )
    assert "raw_vector" not in rec.to_dict()


def test_embedding_record_to_dict_includes_raw_vector_when_populated():
    rec = EmbeddingRecord(
        embedding_id="emb_0001",
        unit_id="gu_001",
        model_id="m",
        model_hash_or_id="sha256:abc",
        dimensions=4,
        vector_ref="opaque://store/emb_0001",
        embedding_hash="sha256:def",
        purpose="document_summary_embedding",
        created_at="2026-05-16T00:00:00Z",
        raw_vector=[0.1, 0.2, 0.3, 0.4],
    )
    d = rec.to_dict()
    assert d["raw_vector"] == [0.1, 0.2, 0.3, 0.4]
