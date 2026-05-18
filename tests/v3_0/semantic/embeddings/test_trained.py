"""Tests for the ``gallodoc_bge_m3_v1`` trained-embedder adapter shell.

The adapter ships in the open-source distribution; the weights live
elsewhere. These tests pin the no-weights contract: without a weights
path, ``available()`` is False and ``embed()`` raises with a hint.
"""

from __future__ import annotations

import pytest

from gallodoc.semantic.embeddings import (
    EMBEDDING_ADAPTERS,
    GalloDocBgeM3V1EmbeddingAdapter,
)


_ENV_VAR = "GALLODOC_BGE_M3_V1_WEIGHTS"


def test_registered_in_embedding_adapters():
    assert "gallodoc_bge_m3_v1" in EMBEDDING_ADAPTERS
    assert EMBEDDING_ADAPTERS["gallodoc_bge_m3_v1"] is GalloDocBgeM3V1EmbeddingAdapter


def test_adapter_static_attributes():
    assert GalloDocBgeM3V1EmbeddingAdapter.slug == "gallodoc_bge_m3_v1"
    assert GalloDocBgeM3V1EmbeddingAdapter.version == "3.0.0"
    assert GalloDocBgeM3V1EmbeddingAdapter.model_id == "gallodoc-bge-m3-v1"
    assert GalloDocBgeM3V1EmbeddingAdapter.dimensions == 256


def test_available_returns_false_without_weights(monkeypatch):
    monkeypatch.delenv(_ENV_VAR, raising=False)
    assert GalloDocBgeM3V1EmbeddingAdapter.available() is False


def test_embed_without_weights_raises(monkeypatch):
    monkeypatch.delenv(_ENV_VAR, raising=False)
    adapter = GalloDocBgeM3V1EmbeddingAdapter()
    with pytest.raises(RuntimeError) as excinfo:
        adapter.embed(["hello world"])
    assert "scripts/train_gallodoc_embedder.py" in str(excinfo.value)


def test_embed_empty_list_returns_empty(monkeypatch):
    monkeypatch.delenv(_ENV_VAR, raising=False)
    adapter = GalloDocBgeM3V1EmbeddingAdapter()
    # Must never raise on empty input (EmbeddingAdapter contract).
    assert adapter.embed([]) == []


def test_invalid_purpose_raises():
    with pytest.raises(ValueError):
        GalloDocBgeM3V1EmbeddingAdapter(purpose="not_a_real_purpose")


def test_env_var_picked_up(monkeypatch, tmp_path):
    monkeypatch.setenv(_ENV_VAR, str(tmp_path))
    adapter = GalloDocBgeM3V1EmbeddingAdapter()
    assert adapter.weights_path == str(tmp_path)


def test_weights_path_argument_overrides_env(monkeypatch, tmp_path):
    monkeypatch.setenv(_ENV_VAR, str(tmp_path / "env_dir"))
    adapter = GalloDocBgeM3V1EmbeddingAdapter(weights_path=str(tmp_path / "arg_dir"))
    assert adapter.weights_path == str(tmp_path / "arg_dir")
