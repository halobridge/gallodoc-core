"""Reproducibility tests for the embeddings examples.

For each (input, expected_output) pair under
``examples/v3_0/embeddings/`` we:

1. Run ``apply_embeddings`` on the committed input.
2. Diff against the committed expected output (stabilizing the
   per-run ``created_at`` timestamps — the ``local_stub`` adapter is
   deterministic on text but not on time).
3. Validate the committed expected output passes ``validate_envelope``.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from gallodoc.semantic.embeddings import (
    LocalStubEmbeddingAdapter,
    apply_embeddings,
)
from gallodoc.validation import validate_envelope


PACKAGE_ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_DIR = PACKAGE_ROOT / "examples" / "v3_0" / "embeddings"


def _stabilize(envelope: dict) -> dict:
    """Replace per-run-varying fields (``created_at`` on embeddings)
    with a fixed sentinel so diffs are deterministic.
    """
    e = copy.deepcopy(envelope)
    embeddings = (e.get("gallounits") or {}).get("embeddings") or []
    for rec in embeddings:
        if isinstance(rec, dict) and "created_at" in rec:
            rec["created_at"] = "<stabilized>"
    return e


def test_examples_directory_present():
    assert EXAMPLES_DIR.is_dir()
    assert (EXAMPLES_DIR / "README.md").is_file()


def test_default_output_reproduces_from_input():
    src = json.loads(
        (EXAMPLES_DIR / "input_envelope.json").read_text(encoding="utf-8")
    )
    expected = json.loads(
        (EXAMPLES_DIR / "output_envelope.gdoc.json").read_text(encoding="utf-8")
    )
    actual = apply_embeddings(
        src,
        LocalStubEmbeddingAdapter(),
        "document_summary_embedding",
    )
    assert _stabilize(actual) == _stabilize(expected)


def test_include_vector_output_reproduces_from_input():
    src = json.loads(
        (
            EXAMPLES_DIR
            / "input_envelope_with_raw_vectors_authorized.json"
        ).read_text(encoding="utf-8")
    )
    expected = json.loads(
        (
            EXAMPLES_DIR / "output_envelope_with_raw_vectors.gdoc.json"
        ).read_text(encoding="utf-8")
    )
    actual = apply_embeddings(
        src,
        LocalStubEmbeddingAdapter(),
        "document_summary_embedding",
        include_vector=True,
    )
    assert _stabilize(actual) == _stabilize(expected)


def test_default_output_validates_as_v3():
    env = json.loads(
        (EXAMPLES_DIR / "output_envelope.gdoc.json").read_text(encoding="utf-8")
    )
    result = validate_envelope(env)
    assert result.valid, [i.message for i in result.issues]


def test_raw_vector_output_validates_as_v3():
    env = json.loads(
        (
            EXAMPLES_DIR / "output_envelope_with_raw_vectors.gdoc.json"
        ).read_text(encoding="utf-8")
    )
    result = validate_envelope(env)
    assert result.valid, [i.message for i in result.issues]


def test_default_output_has_no_raw_vector():
    env = json.loads(
        (EXAMPLES_DIR / "output_envelope.gdoc.json").read_text(encoding="utf-8")
    )
    for rec in env["gallounits"]["embeddings"]:
        assert "raw_vector" not in rec


def test_raw_vector_output_each_vector_is_32_floats():
    env = json.loads(
        (
            EXAMPLES_DIR / "output_envelope_with_raw_vectors.gdoc.json"
        ).read_text(encoding="utf-8")
    )
    for rec in env["gallounits"]["embeddings"]:
        assert "raw_vector" in rec
        assert len(rec["raw_vector"]) == 32
        assert rec["dimensions"] == 32


def test_default_output_has_three_embeddings():
    env = json.loads(
        (EXAMPLES_DIR / "output_envelope.gdoc.json").read_text(encoding="utf-8")
    )
    assert len(env["gallounits"]["embeddings"]) == 3
