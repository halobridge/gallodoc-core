# Model Card — gallodoc-bge-m3-v1

Worked example of [`docs/training/model_card_template.md`](../../../../docs/training/model_card_template.md).
Values are realistic placeholders; do not treat this file as a published
artifact. The real card published with a release lives next to the
weights in the model registry.

## Identity

- **model_id**: gallodoc-bge-m3-v1
- **base_model**: BAAI/bge-m3
- **dimensions**: 256
- **trained_at**: 2026-05-17T00:00:00Z
- **training_dataset_hash**: sha256:7c3a5e9b4f1d2a8c6b0e9f1d3a7c5e2b8d4f6a1c9b3e5d7a0f2c4b6e8d1a3c5f
- **model_weights_location**: hf://halobridge/gallodoc-bge-m3-v1

## intended_use

The `gallodoc-bge-m3-v1` adapter ships six purpose heads suitable for
GalloDoc-envelope-aware retrieval inside the `gallounits.embeddings[]`
shape. It is intended for relationship inference across GalloDocs,
relationship-intent inference from `gallounits.units[].semantic_intent`
(set via the `::semantic_intent` GalloMarkdown block, Decision 5), and
operational intelligence retrieval. It is NOT a general-purpose
sentence embedder.

## limitations

- Not trained on real PHI. Distribution shift is expected against
  domains the synthetic training corpus did not cover.
- Not certified for clinical or legal decision-making.
- The `semantic_intent` vocabulary is the starter set in
  `docs/specs/gallodoc-semantic-intent-v3.md`; extensions in v3.1+
  require re-evaluation on the new labels.
- Adapter dimensions (256) are intentionally small; cross-domain
  recall will benefit from a re-run with a larger projection head if
  your domain warrants it.

## safety_rules

- No raw PHI ever in training data — `assert_no_enterprise_leakage` runs on every pair before training.
- No raw vectors stored in production envelopes by default.
- Decision 5: training pairs MUST have a resolved `semantic_intent` value on source/target units to count as positives.
- Adapter weights ship to an external registry; this repository never carries them.
- The model card MUST accompany every published adapter version.

## training_data_requirements

- Format: `pairs.train.jsonl` from `gallodoc training export-pairs`.
- Schema: see `docs/specs/gallodoc-core-v3-training-lab.md`.
- Positive pair filter: `label == "match"` AND both source + target units carry resolved `semantic_intent`.
- Minimum dataset size: 1000 pairs (recommended; the published v3.0
  card was trained on 1248 synthetic pairs spanning the six purposes).
- Purpose coverage — the trained embedder ships six heads, one per
  `PURPOSE_ENUM` value: `document_summary_embedding`,
  `relationship_embedding`, `entity_context_embedding`,
  `workflow_context_embedding`, `risk_context_embedding`,
  `policy_context_embedding`. Each head must see at least 100
  positive pairs.
- Domain coverage — the synthetic corpus exercises invoice / approver,
  contract / supersession, claim / supporting-document, and case /
  continuation flows. Real-world deployments should top up with their
  domain's positives + 4 hard-negative buckets per Codex 06.

## evaluation

- See `eval_report.json` produced by `scripts/evaluate_gallodoc_embedder.py`.
- Required metrics: `recall_at_5`, `precision_at_5`, `mrr`, `false_positive_rate`, `per_relationship_type_accuracy`, `semantic_intent_accuracy`, `human_review_agreement_rate`.
- Acceptance thresholds: `recall_at_5 >= 0.70`, `false_positive_rate <= 0.10`, `human_review_agreement_rate >= 0.80`.
- Sample report: [`eval_report_example.json`](eval_report_example.json).

## LoRA export

See [`docs/training/lora_export.md`](../../../../docs/training/lora_export.md).
The published v3.0 adapter is hosted at the `model_weights_location`
URI above; pull with the HF CLI or SDK.
