"""Validate ``scripts/evaluate_gallodoc_embedder.py`` output shape.

The eval script is the no-weights-on-disk CI surface. It writes
``eval_report.json`` AND echoes the same JSON to stdout. This test pins
the contract: all 7 required metric keys present, each value typed
correctly, ``pair_count`` matches the input file, and stdout matches
the file.
"""

from __future__ import annotations

import importlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "evaluate_gallodoc_embedder.py"
FIXTURE_PAIRS = REPO_ROOT / "examples" / "v3_0" / "training" / "output_pairs.train.jsonl"


_REQUIRED_METRIC_KEYS = (
    "recall_at_5",
    "precision_at_5",
    "mrr",
    "false_positive_rate",
    "per_relationship_type_accuracy",
    "semantic_intent_accuracy",
    "human_review_agreement_rate",
)


def _load_eval_module():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        return importlib.import_module("evaluate_gallodoc_embedder")
    finally:
        sys.path.pop(0)


def _fixture_pair_count() -> int:
    n = 0
    for line in FIXTURE_PAIRS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n += 1
    return n


def test_required_metric_keys_match_module_constant():
    """Pin the test's view of required keys to the script's constant."""
    mod = _load_eval_module()
    assert tuple(mod.REQUIRED_METRIC_KEYS) == _REQUIRED_METRIC_KEYS


def test_stub_eval_writes_report_with_required_metrics(tmp_path: Path):
    mod = _load_eval_module()
    out = tmp_path / "eval_report.json"
    # Redirect stdout so we can compare against the file.
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = mod.cli_evaluate_gallodoc_embedder(
            pairs_eval=str(FIXTURE_PAIRS),
            weights=None,
            out=str(out),
            purpose="document_summary_embedding",
        )
    finally:
        sys.stdout = old_stdout
    assert rc == 0
    assert out.is_file()

    file_payload = json.loads(out.read_text(encoding="utf-8"))
    stdout_payload = json.loads(buf.getvalue())
    # File and stdout MUST match — downstream consumers may pipe either.
    assert file_payload == stdout_payload

    # Top-level shape.
    assert file_payload["pair_count"] == _fixture_pair_count()
    assert file_payload["mode"] == "stub"
    assert file_payload["purpose"] == "document_summary_embedding"

    metrics = file_payload["metrics"]
    for key in _REQUIRED_METRIC_KEYS:
        assert key in metrics, f"metric key missing: {key}"

    # Type contract: floats for scalars, dicts of floats for buckets.
    assert isinstance(metrics["recall_at_5"], float)
    assert isinstance(metrics["precision_at_5"], float)
    assert isinstance(metrics["mrr"], float)
    assert isinstance(metrics["false_positive_rate"], float)
    assert isinstance(metrics["human_review_agreement_rate"], float)
    assert isinstance(metrics["per_relationship_type_accuracy"], dict)
    assert isinstance(metrics["semantic_intent_accuracy"], dict)
    for v in metrics["per_relationship_type_accuracy"].values():
        assert isinstance(v, float)
    for v in metrics["semantic_intent_accuracy"].values():
        assert isinstance(v, float)


def test_subprocess_eval_round_trips(tmp_path: Path):
    out = tmp_path / "eval_report.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--pairs-eval",
            str(FIXTURE_PAIRS),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, (
        f"subprocess eval failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    file_payload = json.loads(out.read_text(encoding="utf-8"))
    stdout_payload = json.loads(proc.stdout)
    assert file_payload == stdout_payload
    metrics = file_payload["metrics"]
    for key in _REQUIRED_METRIC_KEYS:
        assert key in metrics


def test_bad_purpose_rejected(tmp_path: Path):
    mod = _load_eval_module()
    out = tmp_path / "eval_report.json"
    rc = mod.cli_evaluate_gallodoc_embedder(
        pairs_eval=str(FIXTURE_PAIRS),
        weights=None,
        out=str(out),
        purpose="not_a_real_purpose",
    )
    assert rc == 2


def test_missing_pairs_file_rejected(tmp_path: Path):
    mod = _load_eval_module()
    rc = mod.cli_evaluate_gallodoc_embedder(
        pairs_eval=str(tmp_path / "missing.jsonl"),
        weights=None,
        out=str(tmp_path / "eval_report.json"),
        purpose="document_summary_embedding",
    )
    assert rc == 1
