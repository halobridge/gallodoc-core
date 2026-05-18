# `examples/v3_0/training/embedder/` — Codex 07 worked examples

Three artifacts that together illustrate the end-to-end shape of a
`gallodoc-bge-m3-v1` release. None of these files is a real published
release — they are committed examples sized to be useful as templates
and to validate the contract in tests.

| File | What it demonstrates |
|---|---|
| [`gallodoc_bge_m3_v1_model_card.md`](gallodoc_bge_m3_v1_model_card.md) | A fully-filled-out model card. Every required field from [`docs/training/model_card_template.md`](../../../../docs/training/model_card_template.md) is populated with a realistic placeholder. The `model_weights_location` points at a generic HuggingFace Hub URI; no committed weights. |
| [`eval_report_example.json`](eval_report_example.json) | A sample `eval_report.json` matching the shape `scripts/evaluate_gallodoc_embedder.py` produces. Contains all seven required metric keys, including the Decision 5 `semantic_intent_accuracy` bucket. |
| [`tiny_training_log.json`](tiny_training_log.json) | The `training_log.json` `scripts/train_gallodoc_embedder.py --mode tiny` writes against the synthetic pair fixtures. Demonstrates `mode: "tiny"`, the Decision 5 filter counters, and the dummy-loss field. |

## Reproducing the tiny log

From the repository root:

```bash
cd opensource/gallodoc-core
python scripts/train_gallodoc_embedder.py \
    --pairs-train examples/v3_0/training/output_pairs.train.jsonl \
    --purpose document_summary_embedding \
    --out /tmp/gallodoc_bge_m3_v1_tiny \
    --mode tiny
```

The resulting `/tmp/gallodoc_bge_m3_v1_tiny/document_summary_embedding/training_log.json`
matches `tiny_training_log.json` modulo the `trained_at` field (an ISO
8601 timestamp generated at runtime).

## Reproducing the eval report

```bash
cd opensource/gallodoc-core
python scripts/evaluate_gallodoc_embedder.py \
    --pairs-eval examples/v3_0/training/output_pairs.train.jsonl \
    --out /tmp/gallodoc_bge_m3_v1_eval.json
```

The output's `metrics` keys match `eval_report_example.json` even
though the numeric values will differ (the eval script runs the
deterministic stub when `--weights` is unset).

## Why these examples are committed

Tests in [`tests/v3_0/training/test_embedder_examples.py`](../../../../tests/v3_0/training/test_embedder_examples.py)
validate them. They are also the smallest possible templates a user
needs to publish a `gallodoc-bge-m3-v1`-class adapter.
