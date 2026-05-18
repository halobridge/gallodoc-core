# Training guide

**Audience:** ML engineers reproducing `gallodoc-bge-m3-v1` or training
a downstream variant.
**Reading time:** ~8 minutes.
**Companion specs:**
[`docs/specs/gallodoc-core-v3-training-lab.md`](../specs/gallodoc-core-v3-training-lab.md),
[`docs/specs/gallodoc-core-v3-trained-embedder.md`](../specs/gallodoc-core-v3-trained-embedder.md).

---

## What `gallodoc-bge-m3-v1` is

A contrastive-trained variant of `BAAI/bge-m3` with **6 output heads**
(one per `PURPOSE_ENUM` value: `document_retrieval`,
`semantic_similarity`, `relationship_match`, `intent_match`,
`role_match`, `clustering`). Trained on linker-confirmed relationship
pairs from real envelope traffic.

The training recipe + evaluation harness are open-source. **The trained
weights are not committed to this repo** — they live externally (HF Hub,
S3, internal registry) and load lazily via the
`GALLODOC_BGE_M3_V1_WEIGHTS` env var.

---

## End-to-end training flow

```
envelopes -> training pairs -> hard negatives -> train/dev/test split
   -> train (BGE-M3 + 6 heads + contrastive loss) -> evaluate -> model card
```

Each step is one CLI invocation. The whole thing runs CPU-OK in `--mode
tiny` for CI; full training requires a GPU.

---

## Step 1 — Extract training pairs

```bash
# Single envelope:
gallodoc training export-pairs \
  --input env.gdoc.json \
  --out pairs.jsonl

# Multiple envelopes:
gallodoc training export-pairs \
  --input "envelopes/*.gdoc.json" \
  --out pairs.jsonl \
  --include-hard-negatives \
  --seed 42 \
  --ratios 0.8,0.1,0.1
```

What this produces:

| Label | Source |
|---|---|
| `match` (positive) | Relationships with `status: "confirmed"` AND a `relationship_decisions[]` record, AND a resolved `semantic_intent` on source + target units (Decision 5 filter). |
| `non_match` (negative) | Relationships with `status: "rejected"` AND a decision record. |
| `uncertain` | Relationships with `status: "suggested"` (no decision yet). Used for ablation, NOT for training. |
| `hard_negative` | Generated synthetically (see below). |

The `assert_pairs_clean` privacy gate runs on every pair — no skip
path. If a pair would leak enterprise data, the export aborts.

### The four hard-negative strategies

| Strategy | Generates |
|---|---|
| `same_org_wrong_person` | Same organization, wrong contact. |
| `same_vendor_wrong_invoice` | Same vendor, different invoice number. |
| `similar_clause_different_obligation` | Same clause text, different obligation. |
| `same_customer_name_different_domain` | Same customer name, different email domain. |

All four are deterministic. `--seed 42` ensures the same pair always
lands in the same split.

---

## Step 2 — Train the embedder

```bash
# Tiny mode — CI smoke test (CPU OK, seconds):
python scripts/train_gallodoc_embedder.py \
  --pairs examples/v3_0/training/tiny_pairs.jsonl \
  --mode tiny \
  --out tiny_model/

# Full training (GPU recommended):
python scripts/train_gallodoc_embedder.py \
  --pairs pairs.jsonl \
  --mode full \
  --base-model BAAI/bge-m3 \
  --out gallodoc-bge-m3-v1/
```

What the recipe does:

1. Load BGE-M3 as the base encoder.
2. Add 6 heads (one per `PURPOSE_ENUM` value).
3. For each pair, compute contrastive loss with the head matching the
   pair's purpose.
4. Apply Decision 5 filter: pairs lacking resolved `semantic_intent`
   on source + target are dropped from the positive set.
5. Save weights + a training log (`training_log.json`).

---

## Step 3 — Evaluate

```bash
python scripts/evaluate_gallodoc_embedder.py \
  --model gallodoc-bge-m3-v1/ \
  --eval-pairs eval_pairs.jsonl \
  --out eval_report.json
```

The eval report contains **seven required metrics**:

| Metric | What it measures |
|---|---|
| `recall_at_5` | Recall of the correct match in the top 5 retrieved. |
| `precision_at_5` | Precision of the top 5 retrieved. |
| `mrr` | Mean reciprocal rank. |
| `false_positive_rate` | Match-confidence above threshold for non-matches. |
| `per_relationship_type_accuracy` | Breakdown by `relationship_type`. |
| `semantic_intent_accuracy` | Per-`semantic_intent` accuracy (Decision 5). |
| `human_review_agreement_rate` | Agreement with human-confirmed positives. |

A model card template lives at
`docs/training/model_card_template.md`. Required fields:
`intended_use`, `limitations`, `safety_rules`,
`training_data_requirements`, `evaluation`.

---

## Step 4 — Ship the adapter

```python
# In your runtime:
import os
os.environ["GALLODOC_BGE_M3_V1_WEIGHTS"] = "/path/to/weights/"

from gallodoc.semantic.embeddings import get_adapter

adapter = get_adapter("gallodoc_bge_m3_v1")
assert adapter.available()
```

The adapter's `available()` returns `False` until weights are
configured — the package never carries weights itself.

---

## The "no weights in repo" rule

The release safety gate (check #10 — `no_model_weights_committed`)
scans for:

```
*.bin   *.safetensors   *.pt   *.ckpt   *.onnx   *.gguf
```

A second-line `test_no_weights_in_repo.py` regression test runs in CI.
If you accidentally check in a weights file, both checks will fail.

---

## Ablation guidance

The Codex 07 spec is explicit that:

1. **Decision 5 filter is load-bearing.** Pairs without resolved
   `semantic_intent` on both ends are not training positives. If you
   want a baseline ablation, run with the filter relaxed and compare
   `semantic_intent_accuracy` against the filtered run.
2. **Hard negatives are not optional in the full training run.**
   Without `--include-hard-negatives`, the model overfits to
   easy-to-match positives and `false_positive_rate` blows up.
3. **The 6 heads are not interchangeable.** They train end-to-end on
   the same encoder but differentiate the task; collapsing them to a
   single head trades `relationship_match` and `intent_match`
   accuracy for marginal gains in `document_retrieval`.

---

## Privacy posture during training

Training data is `TrainingPair[]` exported by
`gallodoc training export-pairs`. Every pair has already passed
`assert_pairs_clean`. The pairs file MAY contain hashed identifiers
and resolved `semantic_intent` strings; it MUST NOT contain raw PHI /
PII / secrets / OAuth tokens.

For the trained model itself:

- The model can encode semantic structure that approximates training
  data. This is true of any trained model.
- The recipe runs `assert_no_enterprise_leakage` on every pair before
  it enters the training set.
- The model card template requires populating `safety_rules` with the
  applicable limitations.

---

## Reproducibility

Every step is deterministic given:

- `--seed 42` (default).
- Same base model.
- Same `pairs.jsonl` (the `assert_pairs_clean` gate is stable; same
  envelopes → same pairs in the same order).

This means two engineers running the same recipe on the same inputs
will produce bit-identical weights (within float precision).

---

## What ships with the training lab

| File | Role |
|---|---|
| `gallodoc/training/__init__.py` | Public API. |
| `gallodoc/training/pairs.py` | `TrainingPair` + `extract_pairs_from_envelope`. |
| `gallodoc/training/hard_negatives.py` | The four strategies. |
| `gallodoc/training/split.py` | Deterministic train/dev/test splitter. |
| `gallodoc/training/safety.py` | `assert_pairs_clean`. |
| `gallodoc/training/cli.py` | The `gallodoc training` subcommand. |
| `scripts/train_gallodoc_embedder.py` | The training recipe. |
| `scripts/evaluate_gallodoc_embedder.py` | The evaluation harness. |
| `examples/v3_0/training/` | Small fixture set + tiny pairs. |
| `examples/v3_0/training/embedder/` | Tiny training log + eval report. |
| `docs/training/model_card_template.md` | The required model-card fields. |
| `docs/training/lora_export.md` | LoRA export docs for parameter-efficient training. |

---

## Further reading

- Spec: [`docs/specs/gallodoc-core-v3-training-lab.md`](../specs/gallodoc-core-v3-training-lab.md).
- Spec: [`docs/specs/gallodoc-core-v3-trained-embedder.md`](../specs/gallodoc-core-v3-trained-embedder.md).
- Embeddings (the inference side):
  [`semantic-encoder-guide.md`](semantic-encoder-guide.md).
- Linker (the source of positives):
  [`linker-guide.md`](linker-guide.md).
