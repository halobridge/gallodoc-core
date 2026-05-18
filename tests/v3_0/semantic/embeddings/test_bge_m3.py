"""Tests for the bge_m3 embedding adapter.

The real model is huge and the [semantic] extra may not be installed
in CI. These tests cover the lightweight surface (metadata, available,
ImportError on missing deps) and skip the real embed test when the
backend isn't present.
"""

from __future__ import annotations

import importlib.util

import pytest

from gallodoc.semantic.embeddings.bge_m3 import BgeM3EmbeddingAdapter


_HAS_FLAG = importlib.util.find_spec("FlagEmbedding") is not None
_HAS_ST = importlib.util.find_spec("sentence_transformers") is not None


def test_metadata_matches_spec():
    adapter = BgeM3EmbeddingAdapter()
    assert adapter.slug == "bge_m3"
    assert adapter.version == "3.0.0"
    assert adapter.model_id == "BAAI/bge-m3"
    assert adapter.dimensions == 1024


def test_available_returns_bool_without_raising():
    # Must never raise — even on minimal installs.
    result = BgeM3EmbeddingAdapter.available()
    assert isinstance(result, bool)
    # Sanity-check the disjunction.
    assert result == (_HAS_FLAG or _HAS_ST)


@pytest.mark.skipif(
    _HAS_FLAG or _HAS_ST,
    reason="bge_m3 backend is installed — covered by the live test below",
)
def test_embed_raises_helpful_import_error_without_backend():
    adapter = BgeM3EmbeddingAdapter()
    with pytest.raises(ImportError) as exc_info:
        adapter.embed(["hello"])
    msg = str(exc_info.value)
    assert "gallodoc[semantic]" in msg


def test_embed_empty_input_never_raises():
    # Even if backends are missing, the empty-list shortcut must work
    # (callers use this to probe the adapter).
    adapter = BgeM3EmbeddingAdapter()
    assert adapter.embed([]) == []


@pytest.mark.skipif(
    not (_HAS_FLAG or _HAS_ST),
    reason="bge_m3 backend not installed — install [semantic] extra to run",
)
def test_embed_real_model_returns_1024_dim_vector():
    # Heavy test — only runs when the extras are present locally.
    adapter = BgeM3EmbeddingAdapter()
    vectors = adapter.embed(["the quick brown fox"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 1024


def test_bge_m3_is_exported_from_package():
    from gallodoc.semantic.embeddings import (  # noqa: PLC0415
        BgeM3EmbeddingAdapter as Exported,
    )

    assert Exported is BgeM3EmbeddingAdapter
