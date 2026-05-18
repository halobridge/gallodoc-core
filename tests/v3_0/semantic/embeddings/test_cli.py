"""Tests for the ``gallodoc semantic embed`` CLI subcommand."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.cli.main import main as cli_main
from gallodoc.semantic.embeddings.cli import cli_semantic_embed
from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


def _envelope_with_units(*, raw_vectors_stored: bool = False) -> dict:
    env = minimal_v3_envelope()
    env["gallounits"]["units"] = [
        {
            "unit_id": "gu_001",
            "unit_type": "sentence",
            "text_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "content_summary": "Vendor invoice total is $1,234.56.",
        },
    ]
    if raw_vectors_stored:
        env["safety_profile"] = {"raw_vectors_stored": True}
    return env


def _write(tmp_path: Path, name: str, env: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(env), encoding="utf-8")
    return p


def test_local_stub_produces_valid_v3_envelope(tmp_path: Path):
    src = _write(tmp_path, "input.json", _envelope_with_units())
    out = tmp_path / "output.json"
    rc = cli_semantic_embed(
        input_path=str(src),
        adapter_name="local_stub",
        purpose="document_summary_embedding",
        out_path=str(out),
        include_vector=False,
    )
    assert rc == 0
    assert out.exists()
    result = json.loads(out.read_text(encoding="utf-8"))
    val = validate_envelope(result)
    assert val.valid, f"validation failed: {[i.message for i in val.issues]}"
    assert len(result["gallounits"]["embeddings"]) == 1


def test_bad_adapter_name_returns_non_zero(tmp_path: Path):
    src = _write(tmp_path, "input.json", _envelope_with_units())
    out = tmp_path / "output.json"
    rc = cli_semantic_embed(
        input_path=str(src),
        adapter_name="not_a_real_adapter",
        purpose="document_summary_embedding",
        out_path=str(out),
        include_vector=False,
    )
    assert rc != 0
    assert not out.exists()


def test_bad_purpose_returns_non_zero(tmp_path: Path):
    src = _write(tmp_path, "input.json", _envelope_with_units())
    out = tmp_path / "output.json"
    rc = cli_semantic_embed(
        input_path=str(src),
        adapter_name="local_stub",
        purpose="not_a_real_purpose",
        out_path=str(out),
        include_vector=False,
    )
    assert rc != 0
    assert not out.exists()


def test_missing_input_returns_non_zero(tmp_path: Path):
    out = tmp_path / "output.json"
    rc = cli_semantic_embed(
        input_path=str(tmp_path / "does_not_exist.json"),
        adapter_name="local_stub",
        purpose="document_summary_embedding",
        out_path=str(out),
        include_vector=False,
    )
    assert rc != 0


def test_include_vector_without_safety_profile_returns_non_zero(tmp_path: Path):
    src = _write(tmp_path, "input.json", _envelope_with_units(raw_vectors_stored=False))
    out = tmp_path / "output.json"
    rc = cli_semantic_embed(
        input_path=str(src),
        adapter_name="local_stub",
        purpose="document_summary_embedding",
        out_path=str(out),
        include_vector=True,
    )
    assert rc != 0
    assert not out.exists()


def test_include_vector_with_safety_profile_populates_raw_vector(tmp_path: Path):
    src = _write(tmp_path, "input.json", _envelope_with_units(raw_vectors_stored=True))
    out = tmp_path / "output.json"
    rc = cli_semantic_embed(
        input_path=str(src),
        adapter_name="local_stub",
        purpose="document_summary_embedding",
        out_path=str(out),
        include_vector=True,
    )
    assert rc == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    for rec in result["gallounits"]["embeddings"]:
        assert "raw_vector" in rec
        assert len(rec["raw_vector"]) == rec["dimensions"]


def test_invalid_json_input_returns_non_zero(tmp_path: Path):
    src = tmp_path / "input.json"
    src.write_text("{not valid json", encoding="utf-8")
    out = tmp_path / "output.json"
    rc = cli_semantic_embed(
        input_path=str(src),
        adapter_name="local_stub",
        purpose="document_summary_embedding",
        out_path=str(out),
        include_vector=False,
    )
    assert rc != 0


def test_main_cli_routes_to_semantic_embed(tmp_path: Path):
    src = _write(tmp_path, "input.json", _envelope_with_units())
    out = tmp_path / "output.json"
    rc = cli_main(
        [
            "semantic",
            "embed",
            str(src),
            "--adapter",
            "local_stub",
            "--purpose",
            "document_summary_embedding",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    assert out.exists()


def test_main_cli_default_adapter_is_local_stub(tmp_path: Path):
    src = _write(tmp_path, "input.json", _envelope_with_units())
    out = tmp_path / "output.json"
    rc = cli_main(
        [
            "semantic",
            "embed",
            str(src),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    embeddings = result["gallounits"]["embeddings"]
    assert len(embeddings) == 1
    # default adapter slug carries through to model_id.
    assert embeddings[0]["model_id"] == "gallodoc.embedder.local_stub.v3.0"
    assert embeddings[0]["purpose"] == "document_summary_embedding"


def test_embedding_adapters_registry_has_four_entries():
    from gallodoc.semantic.embeddings import EMBEDDING_ADAPTERS  # noqa: PLC0415

    assert set(EMBEDDING_ADAPTERS) == {
        "local_stub",
        "bge_m3",
        "sentence_transformers",
        "gallodoc_bge_m3_v1",
    }


def test_gallodoc_bge_m3_v1_without_weights_fails_gracefully(
    tmp_path: Path, monkeypatch, capsys
):
    """``--adapter gallodoc_bge_m3_v1`` without weights returns non-zero
    and writes a stderr message pointing users at the env var or the
    training script. The CLI must not crash."""
    monkeypatch.delenv("GALLODOC_BGE_M3_V1_WEIGHTS", raising=False)
    src = _write(tmp_path, "input.json", _envelope_with_units())
    out = tmp_path / "output.json"
    rc = cli_semantic_embed(
        input_path=str(src),
        adapter_name="gallodoc_bge_m3_v1",
        purpose="document_summary_embedding",
        out_path=str(out),
        include_vector=False,
    )
    assert rc != 0
    assert not out.exists()
    captured = capsys.readouterr()
    # The CLI's generic exception handler prints the adapter's message,
    # which mentions both the env var and the training script.
    assert "GALLODOC_BGE_M3_V1_WEIGHTS" in captured.err
    assert "scripts/train_gallodoc_embedder.py" in captured.err
