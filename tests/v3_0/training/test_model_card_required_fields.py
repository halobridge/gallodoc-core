"""Validate the trained-embedder model card template.

Asserts every required field is present (the template is the contract
example releases must satisfy), that the six purpose values from Codex
05's PURPOSE_ENUM appear in the training-data section, and that the
Decision 5 safety rule about ``semantic_intent`` is present verbatim.
"""

from __future__ import annotations

from pathlib import Path

from gallodoc.semantic.embeddings.base import PURPOSE_ENUM


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = REPO_ROOT / "docs" / "training" / "model_card_template.md"


# Every required model-card field. The list is duplicated here (not
# imported from the spec) so the test fails if either the template or
# the spec drifts unilaterally.
_REQUIRED_FIELDS: tuple[str, ...] = (
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


# The Decision 5 safety rule must appear verbatim in the template's
# Safety rules section so every published card carries it forward.
_DECISION_5_RULE = (
    "Decision 5: training pairs MUST have a resolved `semantic_intent` "
    "value on source/target units to count as positives."
)


def _template_text() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def test_template_exists():
    assert TEMPLATE_PATH.is_file(), (
        f"model card template missing at {TEMPLATE_PATH}"
    )


def test_template_has_all_required_fields():
    text = _template_text()
    missing = [f for f in _REQUIRED_FIELDS if f not in text]
    assert not missing, f"template missing required fields: {missing}"


def test_template_lists_all_six_purposes():
    text = _template_text()
    missing = [p for p in PURPOSE_ENUM if p not in text]
    assert not missing, (
        f"template does not mention purpose values: {missing}"
    )


def test_template_carries_decision_5_safety_rule():
    text = _template_text()
    assert _DECISION_5_RULE in text, (
        "Decision 5 semantic_intent safety rule not found verbatim in "
        "the model card template"
    )
