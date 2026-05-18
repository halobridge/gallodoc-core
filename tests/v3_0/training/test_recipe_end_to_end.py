"""End-to-end smoke: export pairs → train (tiny) → evaluate.

Precursor to the prompt-10 release demo. Chains the Codex 06 exporter,
the Codex 07 tiny-mode trainer, and the Codex 07 stub evaluator over
the committed input envelopes fixture. Each stage's output flows into
the next; the final assertion is that the eval report carries the
seven required metric keys.
"""

from __future__ import annotations

import importlib
import io
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_ENVELOPES = (
    REPO_ROOT / "examples" / "v3_0" / "training" / "input_envelopes.json"
)


def _load_script_module(name: str):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.pop(0)


def test_export_train_eval_chain(tmp_path: Path, monkeypatch):
    """Run the three stages end-to-end on synthetic fixtures."""
    # ---- Stage 1: export pairs from envelopes ------------------------
    from gallodoc.training.cli import cli_training_export_pairs  # noqa: PLC0415

    pairs_out = tmp_path / "pairs"
    pairs_out.mkdir()
    pairs_jsonl = pairs_out / "pairs.train.jsonl"
    rc = cli_training_export_pairs(
        input_path=str(INPUT_ENVELOPES),
        out_path=str(pairs_jsonl),
        seed=42,
        ratios_str=None,
        include_hard_negatives=False,
    )
    assert rc == 0
    assert pairs_jsonl.exists()

    # ---- Stage 2: tiny-mode train -----------------------------------
    train_mod = _load_script_module("train_gallodoc_embedder")
    wts_dir = tmp_path / "wts"
    rc = train_mod.cli_train_gallodoc_embedder(
        pairs_train=str(pairs_jsonl),
        pairs_dev=None,
        purpose="document_summary_embedding",
        out=str(wts_dir),
        mode="tiny",
        base_model="BAAI/bge-m3",
    )
    assert rc == 0
    training_log_path = wts_dir / "document_summary_embedding" / "training_log.json"
    assert training_log_path.is_file()
    training_log = json.loads(training_log_path.read_text(encoding="utf-8"))
    assert training_log["mode"] == "tiny"
    # The committed input_envelopes.json yields at least 1 match + 1
    # non_match + 1 uncertain pair. Be loose; tighten if the fixture
    # changes intentionally.
    assert training_log["pairs_seen"] >= 3

    # ---- Stage 3: evaluate -----------------------------------------
    eval_mod = _load_script_module("evaluate_gallodoc_embedder")
    eval_out = tmp_path / "eval_report.json"
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = eval_mod.cli_evaluate_gallodoc_embedder(
            pairs_eval=str(pairs_jsonl),
            weights=None,
            out=str(eval_out),
            purpose="document_summary_embedding",
        )
    finally:
        sys.stdout = old_stdout
    assert rc == 0
    assert eval_out.is_file()
    report = json.loads(eval_out.read_text(encoding="utf-8"))
    for key in (
        "recall_at_5",
        "precision_at_5",
        "mrr",
        "false_positive_rate",
        "per_relationship_type_accuracy",
        "semantic_intent_accuracy",
        "human_review_agreement_rate",
    ):
        assert key in report["metrics"], f"metric missing in chained eval: {key}"
    # Stdout == file (eval contract).
    assert json.loads(buf.getvalue()) == report
