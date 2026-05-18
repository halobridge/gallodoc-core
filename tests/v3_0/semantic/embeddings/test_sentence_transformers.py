"""Tests for the sentence_transformers embedding adapter."""

from __future__ import annotations

import importlib.util

import pytest

from gallodoc.semantic.embeddings.sentence_transformers_adapter import (
    SentenceTransformersEmbeddingAdapter,
)


_HAS_ST = importlib.util.find_spec("sentence_transformers") is not None


def test_metadata_matches_spec():
    adapter = SentenceTransformersEmbeddingAdapter(model_name="all-MiniLM-L6-v2")
    assert adapter.slug == "sentence_transformers"
    assert adapter.version == "3.0.0"
    assert adapter.model_id == "sentence_transformers:all-MiniLM-L6-v2"
    # Dimensions resolves on first embed() call — 0 until then.
    assert adapter.dimensions == 0


def test_default_model_name():
    adapter = SentenceTransformersEmbeddingAdapter()
    assert adapter.model_name == "all-MiniLM-L6-v2"


def test_available_returns_bool_without_raising():
    result = SentenceTransformersEmbeddingAdapter.available()
    assert isinstance(result, bool)
    assert result == _HAS_ST


def test_embed_empty_input_never_raises():
    adapter = SentenceTransformersEmbeddingAdapter()
    assert adapter.embed([]) == []


@pytest.mark.skipif(
    _HAS_ST,
    reason="sentence_transformers is installed — covered by the live test below",
)
def test_embed_raises_helpful_import_error_without_sentence_transformers():
    adapter = SentenceTransformersEmbeddingAdapter()
    with pytest.raises(ImportError) as exc_info:
        adapter.embed(["hello"])
    msg = str(exc_info.value)
    assert "gallodoc[semantic]" in msg


@pytest.mark.skipif(
    not _HAS_ST,
    reason="sentence_transformers not installed — install [semantic] extra to run",
)
def test_embed_real_model_resolves_dimensions():
    # Heavy test — only runs when the extras are present locally.
    adapter = SentenceTransformersEmbeddingAdapter(model_name="all-MiniLM-L6-v2")
    vectors = adapter.embed(["the quick brown fox"])
    assert len(vectors) == 1
    assert adapter.dimensions > 0
    assert len(vectors[0]) == adapter.dimensions


def test_sentence_transformers_is_exported_from_package():
    from gallodoc.semantic.embeddings import (  # noqa: PLC0415
        SentenceTransformersEmbeddingAdapter as Exported,
    )

    assert Exported is SentenceTransformersEmbeddingAdapter
