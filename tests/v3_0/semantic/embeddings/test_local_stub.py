"""Tests for the local_stub embedding adapter."""

from __future__ import annotations

from gallodoc.semantic.embeddings.local_stub import LocalStubEmbeddingAdapter


def test_available_without_extras():
    # No optional dependencies — always available.
    assert LocalStubEmbeddingAdapter.available() is True


def test_embed_single_text_returns_one_vector_of_thirty_two_floats():
    adapter = LocalStubEmbeddingAdapter()
    vectors = adapter.embed(["hello"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 32
    assert all(isinstance(v, float) for v in vectors[0])


def test_embed_empty_input_returns_empty_list():
    adapter = LocalStubEmbeddingAdapter()
    assert adapter.embed([]) == []


def test_embed_empty_string_returns_all_zeros():
    adapter = LocalStubEmbeddingAdapter()
    vectors = adapter.embed([""])
    assert vectors == [[0.0] * 32]


def test_embed_same_text_is_deterministic():
    adapter = LocalStubEmbeddingAdapter()
    a = adapter.embed(["hello world"])
    b = adapter.embed(["hello world"])
    assert a == b


def test_embed_different_texts_produce_different_vectors():
    adapter = LocalStubEmbeddingAdapter()
    a = adapter.embed(["alpha"])
    b = adapter.embed(["beta"])
    assert a != b


def test_embed_values_in_unit_range():
    adapter = LocalStubEmbeddingAdapter()
    vectors = adapter.embed(["the quick brown fox jumps over the lazy dog"])
    for v in vectors[0]:
        assert -1.0 <= v <= 1.0


def test_embed_multiple_texts_returns_one_vector_per_text():
    adapter = LocalStubEmbeddingAdapter()
    vectors = adapter.embed(["alpha", "beta", "gamma"])
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 32


def test_adapter_metadata_matches_spec():
    adapter = LocalStubEmbeddingAdapter()
    assert adapter.slug == "local_stub"
    assert adapter.version == "3.0.0"
    assert adapter.model_id == "gallodoc.embedder.local_stub.v3.0"
    assert adapter.dimensions == 32


def test_local_stub_is_exported_from_package():
    # The package __init__ should export the local_stub adapter so the
    # CLI can pick it up without poking module internals.
    from gallodoc.semantic.embeddings import LocalStubEmbeddingAdapter as Exported

    assert Exported is LocalStubEmbeddingAdapter
