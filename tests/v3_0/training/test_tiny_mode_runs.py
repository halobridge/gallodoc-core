"""``scripts/train_gallodoc_embedder.py --mode tiny`` smoke test.

Exercises the Codex 06 → Codex 07 handoff with the committed pair
fixtures. ``--mode tiny`` finishes in seconds, writes a training_log.json
under ``<out>/<purpose>/``, and writes NO model weights. The
no-weights-on-disk assertion here mirrors the repo-wide guard in
``test_no_weights_in_repo.py``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "train_gallodoc_embedder.py"
FIXTURE_PAIRS = REPO_ROOT / "examples" / "v3_0" / "training" / "output_pairs.train.jsonl"

_WEIGHT_EXTENSIONS = (".bin", ".safetensors", ".pt", ".ckpt", ".onnx", ".gguf")


def _assert_no_weights_written(out_dir: Path) -> None:
    """Walk ``out_dir`` and assert no committed-weight artifact appears."""
    for p in out_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix in _WEIGHT_EXTENSIONS:
            raise AssertionError(
                f"unexpected weights artifact in tiny-mode output: {p}"
            )


@pytest.fixture
def script_env(tmp_path: Path):
    """A clean out directory under tmp_path. Each test gets its own."""
    out = tmp_path / "wts"
    yield out


def test_tiny_mode_via_function_returns_zero(script_env: Path):
    """Library-form call returns 0 and writes the expected log."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        # Import after path manipulation so we hit our script not any
        # site-packages shadow.
        import importlib  # noqa: PLC0415

        mod = importlib.import_module("train_gallodoc_embedder")
        rc = mod.cli_train_gallodoc_embedder(
            pairs_train=str(FIXTURE_PAIRS),
            pairs_dev=None,
            purpose="document_summary_embedding",
            out=str(script_env),
            mode="tiny",
            base_model="BAAI/bge-m3",
        )
    finally:
        sys.path.pop(0)
    assert rc == 0
    log = script_env / "document_summary_embedding" / "training_log.json"
    assert log.is_file(), f"training_log.json not written at {log}"
    payload = json.loads(log.read_text(encoding="utf-8"))
    for key in (
        "mode",
        "purpose",
        "trained_at",
        "epochs",
        "pairs_seen",
        "positives_in",
        "positives_kept",
        "filtered_no_intent",
        "negatives",
        "uncertain",
        "dummy_loss_final",
    ):
        assert key in payload, f"training_log.json missing {key}"
    assert payload["mode"] == "tiny"
    assert payload["purpose"] == "document_summary_embedding"
    assert payload["pairs_seen"] == 3  # 3 pairs in the committed fixture
    _assert_no_weights_written(script_env)


def test_tiny_mode_via_subprocess_returns_zero(script_env: Path):
    """Subprocess invocation matches the library-form behaviour."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--pairs-train",
            str(FIXTURE_PAIRS),
            "--purpose",
            "document_summary_embedding",
            "--out",
            str(script_env),
            "--mode",
            "tiny",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, (
        f"tiny mode subprocess failed:\nstdout={proc.stdout}\n"
        f"stderr={proc.stderr}"
    )
    log = script_env / "document_summary_embedding" / "training_log.json"
    assert log.is_file()
    _assert_no_weights_written(script_env)


def test_tiny_mode_bad_purpose_rejected(script_env: Path, tmp_path: Path):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import importlib  # noqa: PLC0415

        mod = importlib.import_module("train_gallodoc_embedder")
        rc = mod.cli_train_gallodoc_embedder(
            pairs_train=str(FIXTURE_PAIRS),
            pairs_dev=None,
            purpose="not_a_real_purpose",
            out=str(script_env),
            mode="tiny",
            base_model="BAAI/bge-m3",
        )
    finally:
        sys.path.pop(0)
    assert rc == 2


def test_tiny_mode_missing_input_rejected(tmp_path: Path):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import importlib  # noqa: PLC0415

        mod = importlib.import_module("train_gallodoc_embedder")
        rc = mod.cli_train_gallodoc_embedder(
            pairs_train=str(tmp_path / "does_not_exist.jsonl"),
            pairs_dev=None,
            purpose="document_summary_embedding",
            out=str(tmp_path / "wts"),
            mode="tiny",
            base_model="BAAI/bge-m3",
        )
    finally:
        sys.path.pop(0)
    assert rc == 1


def test_tiny_mode_drops_intentless_positive(tmp_path: Path):
    """Decision 5 filter: positives without semantic_intent are dropped.

    Synthesizes a 2-pair fixture: one positive with intent, one positive
    without. The training log should report ``positives_in=2``,
    ``positives_kept=1``, ``filtered_no_intent=1``.
    """
    pairs = [
        {
            "pair_id": "pair_with_intent",
            "source_gallodoc_ref": "doc_a",
            "target_gallodoc_ref": "doc_b",
            "relationship_type": "approved_by",
            "semantic_intent": "invoice_to_employee_approver",
            "label": "match",
            "evidence_refs": [],
            "reviewer_decision": None,
            "confidence": 0.95,
            "discovered_by": "human_review",
            "created_at": "2026-05-17T00:00:00Z",
        },
        {
            "pair_id": "pair_without_intent",
            "source_gallodoc_ref": "doc_a",
            "target_gallodoc_ref": "doc_c",
            "relationship_type": "approved_by",
            "semantic_intent": None,
            "label": "match",
            "evidence_refs": [],
            "reviewer_decision": None,
            "confidence": 0.93,
            "discovered_by": "human_review",
            "created_at": "2026-05-17T00:00:00Z",
        },
    ]
    fixture = tmp_path / "pairs.train.jsonl"
    with fixture.open("w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p) + "\n")
    out_dir = tmp_path / "wts"

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import importlib  # noqa: PLC0415

        mod = importlib.import_module("train_gallodoc_embedder")
        rc = mod.cli_train_gallodoc_embedder(
            pairs_train=str(fixture),
            pairs_dev=None,
            purpose="document_summary_embedding",
            out=str(out_dir),
            mode="tiny",
            base_model="BAAI/bge-m3",
        )
    finally:
        sys.path.pop(0)
    assert rc == 0
    log = json.loads(
        (out_dir / "document_summary_embedding" / "training_log.json")
        .read_text(encoding="utf-8")
    )
    assert log["positives_in"] == 2
    assert log["positives_kept"] == 1
    assert log["filtered_no_intent"] == 1
