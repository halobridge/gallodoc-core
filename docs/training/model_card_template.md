# Model Card — <fill model_id>

Template for trained-embedder releases of `gallodoc-bge-m3-v1` (and
future variants). Every field marked `<fill>` MUST be filled before
publishing weights. Fields are validated by
`tests/v3_0/training/test_model_card_required_fields.py`.

## Identity

- **model_id**: <fill>
- **base_model**: <fill>
- **dimensions**: <fill>
- **trained_at**: <fill ISO 8601>
- **training_dataset_hash**: <fill sha256:...>
- **model_weights_location**: <fill — externally-resolvable URI, never a committed path>

## intended_use

<fill — one paragraph>

## limitations

<fill — known failure modes, false-positive patterns, distribution-shift caveats>

## safety_rules

- No raw PHI ever in training data — `assert_no_enterprise_leakage` runs on every pair before training.
- No raw vectors stored in production envelopes by default.
- Decision 5: training pairs MUST have a resolved `semantic_intent` value on source/target units to count as positives.
- <fill — model-specific safety rules>

## training_data_requirements

- Format: `pairs.train.jsonl` from `gallodoc training export-pairs`.
- Schema: see `docs/specs/gallodoc-core-v3-training-lab.md`.
- Positive pair filter: `label == "match"` AND both source + target units carry resolved `semantic_intent`.
- Minimum dataset size: <fill — e.g. 1000 pairs>.
- Purpose coverage — the trained embedder ships six heads, one per
  `PURPOSE_ENUM` value: `document_summary_embedding`,
  `relationship_embedding`, `entity_context_embedding`,
  `workflow_context_embedding`, `risk_context_embedding`,
  `policy_context_embedding`. The training data should provide
  supervision for each purpose head you intend to publish.
- <fill — domain coverage, recency, etc.>

## evaluation

- See `eval_report.json` produced by `scripts/evaluate_gallodoc_embedder.py`.
- Required metrics: `recall_at_5`, `precision_at_5`, `mrr`, `false_positive_rate`, `per_relationship_type_accuracy`, `semantic_intent_accuracy`, `human_review_agreement_rate`.
- Acceptance thresholds: <fill — e.g. recall_at_5 >= 0.7>.

## LoRA export

- Adapter weights are shipped to an external registry. See
  [`lora_export.md`](lora_export.md) for the directory layout, loader
  hook, and the generic upload guide.
