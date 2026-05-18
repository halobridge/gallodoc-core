"""Validate the committed Codex 07 worked examples.

Three files live under ``examples/v3_0/training/embedder/``:
the filled-in model card, a sample eval report, and a sample tiny-mode
training log. This test pins each one to the contract documented in
the recipe spec.
"""

from __future__ import annotations

import json
from pathlib import Path

from gallodoc.semantic.embeddings.base import PURPOSE_ENUM


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_DIR = REPO_ROOT / "examples" / "v3_0" / "training" / "embedder"
MODEL_CARD = EXAMPLE_DIR / "gallodoc_bge_m3_v1_model_card.md"
EVAL_REPORT = EXAMPLE_DIR / "eval_report_example.json"
TINY_LOG = EXAMPLE_DIR / "tiny_training_log.json"
README = EXAMPLE_DIR / "README.md"


_REQUIRED_MODEL_CARD_FIELDS: tuple[str, ...] = (
    "model_id",
    "base_model",
    "dimensions",
    "trained_at",
    "training_dataset_hash",
    "model_weights_location",
    "intended_use",
    "limitations",
    "safety_rules",
    "training_data_requirements",
    "evaluation",
)


_REQUIRED_METRIC_KEYS: tuple[str, ...] = (
    "recall_at_5",
    "precision_at_5",
    "mrr",
    "false_positive_rate",
    "per_relationship_type_accuracy",
    "semantic_intent_accuracy",
    "human_review_agreement_rate",
)


_REQUIRED_TINY_LOG_KEYS: tuple[str, ...] = (
    "mode",
    "purpose",
    "trained_at",
    "epochs",
    "batch_size",
    "base_model",
    "pairs_seen",
    "positives_in",
    "positives_kept",
    "filtered_no_intent",
    "negatives",
    "uncertain",
    "dummy_loss_final",
)


def test_examples_dir_layout():
    assert EXAMPLE_DIR.is_dir(), f"missing examples dir: {EXAMPLE_DIR}"
    assert MODEL_CARD.is_file()
    assert EVAL_REPORT.is_file()
    assert TINY_LOG.is_file()
    assert README.is_file()


def test_model_card_has_required_fields():
    text = MODEL_CARD.read_text(encoding="utf-8")
    missing = [f for f in _REQUIRED_MODEL_CARD_FIELDS if f not in text]
    assert not missing, f"model card missing fields: {missing}"


def test_model_card_lists_all_six_purposes():
    text = MODEL_CARD.read_text(encoding="utf-8")
    missing = [p for p in PURPOSE_ENUM if p not in text]
    assert not missing, f"model card does not mention purposes: {missing}"


def test_model_card_carries_decision_5_rule():
    text = MODEL_CARD.read_text(encoding="utf-8")
    assert (
        "training pairs MUST have a resolved `semantic_intent` value on source/target units to count as positives"
        in text
    ), "Decision 5 safety rule not present in worked-example model card"


def test_eval_report_example_has_required_metrics():
    payload = json.loads(EVAL_REPORT.read_text(encoding="utf-8"))
    assert payload["mode"] in {"stub", "trained"}
    assert "metrics" in payload
    metrics = payload["metrics"]
    missing = [k for k in _REQUIRED_METRIC_KEYS if k not in metrics]
    assert not missing, f"eval report missing metric keys: {missing}"

    # Type contract — same as scripts/evaluate_gallodoc_embedder.py.
    for k in ("recall_at_5", "precision_at_5", "mrr", "false_positive_rate", "human_review_agreement_rate"):
        assert isinstance(metrics[k], (int, float))
    for k in ("per_relationship_type_accuracy", "semantic_intent_accuracy"):
        assert isinstance(metrics[k], dict)
        for v in metrics[k].values():
            assert isinstance(v, (int, float))


def test_eval_report_intent_buckets_are_in_vocabulary():
    """Intent accuracy keys must come from the published v3 vocabulary."""
    from_spec = {
        "invoice_to_employee_approver",
        "contract_supersedes_contract",
        "patient_to_consent_record",
        "claim_to_supporting_document",
        "case_to_case_continuation",
        "attachment_to_parent_document",
    }
    payload = json.loads(EVAL_REPORT.read_text(encoding="utf-8"))
    seen = set(payload["metrics"]["semantic_intent_accuracy"].keys())
    unknown = seen - from_spec
    assert not unknown, (
        f"semantic_intent_accuracy contains values outside the v3 starter "
        f"vocabulary: {unknown}"
    )


def test_tiny_log_has_required_keys():
    payload = json.loads(TINY_LOG.read_text(encoding="utf-8"))
    missing = [k for k in _REQUIRED_TINY_LOG_KEYS if k not in payload]
    assert not missing, f"tiny training log missing keys: {missing}"
    assert payload["mode"] == "tiny"
    assert payload["purpose"] in PURPOSE_ENUM
