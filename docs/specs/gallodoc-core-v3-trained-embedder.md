# GalloDoc-trained embedder v1 (Codex 07)

**Status:** active (v3.0).
**Slug:** `gallodoc_bge_m3_v1`.
**Adapter file:** [`gallodoc/semantic/embeddings/trained.py`](../../gallodoc/semantic/embeddings/trained.py).
**Recipe entry points:** [`scripts/train_gallodoc_embedder.py`](../../scripts/train_gallodoc_embedder.py),
[`scripts/evaluate_gallodoc_embedder.py`](../../scripts/evaluate_gallodoc_embedder.py).
**Anchor decisions:** locked against the five anchor decisions in
[../../../docs/v3-design/07_decisions.md](../../../docs/v3-design/07_decisions.md).
This prompt is the consumer of **Decision 5** (the `::semantic_intent`
positives filter — see §4 below).

## 1. Overview

This spec ships the **training RECIPE** for the GalloDoc-trained embedder
`gallodoc-bge-m3-v1`. The recipe — scripts, evaluation harness, model
card template, LoRA-export documentation, and the lazy-load adapter
shell — is open-source. **The model weights are NOT in this repository.**
Anyone with the recipe plus a curated `pairs.train.jsonl` (produced by
the Codex 06 training lab) can reproduce the model.

The recipe lives in the open-source distribution because the value of an
open standard is the reproducibility of the artifacts that consume it.
The weights live elsewhere (HaloBridge enterprise model registry, your
internal registry, or HuggingFace Hub) because (a) redistributing model
weights is governance-sensitive, (b) the open-source release pace is
faster than the model-retraining pace, and (c) the no-weights invariant
is enforced by two scans:

- The CI workflow lint job in
  [`.github/workflows/v3-release.yml`](../../../.github/workflows/v3-release.yml)
  fails the build on any committed `*.bin`, `*.safetensors`, `*.pt`,
  `*.ckpt`, `*.onnx`, or `*.gguf`.
- A second-line `tests/v3_0/training/test_no_weights_in_repo.py` test
  fails pytest on the same file extensions.

## 2. Base model

`BAAI/bge-m3` — referenced by HuggingFace id, downloaded at training
time by the user. Not bundled in this repository. The base model is
**frozen** during training; only the per-purpose LoRA projection heads
are updated.

## 3. Training objective

Contrastive pair learning. Positive pairs (`label: "match"`) are pulled
closer in embedding space; negative pairs (`label: "non_match"`) are
pushed apart. Standard cosine-similarity-based contrastive loss
(`MultipleNegativesRankingLoss` or `InfoNCE`, depending on hard-negative
availability). Uncertain pairs (`label: "uncertain"`) are excluded from
the training set in v3.0; v3.1 may revisit using them as soft anchors.

## 4. Relationship-aware training targets

The embedder learns two label spaces simultaneously, kept independent so
the two vocabularies can extend without re-training (Decision 5
rationale):

### `relationship_type` — v2.0 enum, plus six v3 starter targets

- `invoice_to_employee_approver`
- `same_customer`
- `same_contract`
- `website_claim_to_policy`
- `support_ticket_to_customer`
- `operationally_related`

These six v3 starter targets supplement the v2.0
`document_relationships` enum
(`duplicate_of`, `version_of`, `supersedes`, `belongs_to`, `supports`,
`contradicts`, `same_claim`, `same_patient`, `same_customer`,
`same_contract`, `same_invoice`, `derived_from`, `related_to`). The
combined enum is the label space for the relationship-type head.

### `semantic_intent` — the v3.0 starter vocabulary

From [`docs/specs/gallodoc-semantic-intent-v3.md`](gallodoc-semantic-intent-v3.md):

1. `invoice_to_employee_approver`
2. `contract_supersedes_contract`
3. `patient_to_consent_record`
4. `claim_to_supporting_document`
5. `case_to_case_continuation`
6. `attachment_to_parent_document`

This is the label space for the semantic-intent head.

### Decision 5 — `semantic_intent` filter on positives

**Training pairs MUST have a resolved `semantic_intent` on the source/
target units to count as positives for the embedder.** Pairs lacking
intent are dropped from the positive set. They may still feed the
linker's other signals (per Decision 5) but they do not contribute
positive supervision to the embedder.

#### Worked example

Given two pairs from `examples/v3_0/training/output_pairs.train.jsonl`:

```jsonl
{"pair_id": "pair_67d0f470ad3378db", "source_gallodoc_ref": "doc_invoice_001", "target_gallodoc_ref": "doc_employee_042", "relationship_type": "approved_by", "semantic_intent": "invoice_to_employee_approver", "label": "match", ...}
{"pair_id": "pair_2d35cc4d15e57e08", "source_gallodoc_ref": "doc_invoice_001", "target_gallodoc_ref": "doc_employee_123", "relationship_type": "approved_by", "semantic_intent": null, "label": "non_match", ...}
```

The first pair is a positive (`label == "match"`) **AND** carries a
resolved `semantic_intent`. It enters the embedder's positive set.

The second pair has `semantic_intent: null`. Because it is also
`label == "non_match"` the filter is moot — it would have been a
negative anyway. The filter only matters for `label == "match"` rows.

A third pair, were it `label: "match"` AND `semantic_intent: null`,
would be **dropped** from the positive set by the Decision 5 filter. It
would NOT contribute positive supervision.

## 5. Multi-profile output (six heads)

The trained embedder produces six embedding heads, one per `PURPOSE_ENUM`
value (defined in [`gallodoc/semantic/embeddings/base.py`](../../gallodoc/semantic/embeddings/base.py)):

| Purpose | What it encodes |
|---|---|
| `document_summary_embedding` | The whole document, summarized. |
| `relationship_embedding` | A relationship's two sides, for proximity ranking. |
| `entity_context_embedding` | An entity reference, for cross-document linking. |
| `workflow_context_embedding` | A step in a workflow lifecycle. |
| `risk_context_embedding` | A risk pattern from trust/security blocks. |
| `policy_context_embedding` | A policy condition, for matching. |

Each head is a small **LoRA-style projection** on top of the frozen
`BAAI/bge-m3` base. Architecture: **1024-dim base → 256-dim per head.**
Each head is trained and shipped independently — adding a new purpose in
v3.1+ does not require re-training the existing heads.

## 6. Training modes

| Mode | Use | Epochs | Batch | Hardware | CI? |
|---|---|---|---|---|---|
| `--mode tiny` | Smoke-test the pipeline on synthetic fixtures. | 5 | 4 | CPU-OK | yes |
| `--mode standard` | Recommended for real training. | 5–20 | 32 | GPU recommended | no |
| `--mode full` | Full training over a large dataset. | 20+ | 64+ | GPU required | no |

`--mode tiny` runs on `examples/v3_0/training/` fixtures in seconds and
is the only mode CI exercises. The recipe contains the standard / full
skeletons; users plug in the real training loop when they run real
training.

## 7. Evaluation metrics

`scripts/evaluate_gallodoc_embedder.py` emits the following metrics in
`eval_report.json`:

| Metric | Type | Notes |
|---|---|---|
| `recall_at_5` | float | Recall@5 over the eval pair set. |
| `precision_at_5` | float | Precision@5. |
| `mrr` | float | Mean reciprocal rank. |
| `false_positive_rate` | float | False-positive rate vs. `non_match` pairs. |
| `per_relationship_type_accuracy` | dict[str, float] | Keyed on relationship_type. |
| `semantic_intent_accuracy` | dict[str, float] | Keyed on intent — per Decision 5. |
| `human_review_agreement_rate` | float | Agreement with `relationship_decisions[]` ground truth. |

The eval script writes the report to `--out` (default `eval_report.json`)
AND emits the same JSON to stdout so a CI step can pipe it.

## 8. LoRA / adapter export

The trainer outputs **LoRA adapter weights only** — small per-head
deltas on top of the frozen base. Full directory layout, loading
patterns, and a generic upload guide live in
[`../training/lora_export.md`](../training/lora_export.md). The LoRA
files (`adapter_model.safetensors`) are NOT committed; production users
upload them to their own model registry and reference them by URI in
the model card.

## 9. Model card template

Required fields (full template in
[`docs/training/model_card_template.md`](../training/model_card_template.md)):

- `model_id`
- `base_model`
- `dimensions`
- `trained_at` (ISO 8601 UTC)
- `training_dataset_hash` (SHA-256)
- `model_weights_location` — always an externally-resolvable URI, never
  a committed path
- `intended_use`
- `limitations`
- `safety_rules`
- `training_data_requirements`
- `evaluation`

## 10. Adapter shipped in this PR

The repository ships
[`gallodoc/semantic/embeddings/trained.py`](../../gallodoc/semantic/embeddings/trained.py)
with the `GalloDocBgeM3V1EmbeddingAdapter` class. The adapter is
**lazy-import + lazy-load**:

- Without weights configured (`GALLODOC_BGE_M3_V1_WEIGHTS` unset and no
  `weights_path` argument), `available()` returns `False`.
- Calling `embed()` without weights raises `RuntimeError` with a helpful
  hint pointing to `scripts/train_gallodoc_embedder.py`.
- The heavy dependencies (`sentence_transformers`, `peft`) are imported
  inside `embed()`, never at module load time.

**The recipe is what we ship; the weights live elsewhere.**

## 11. Forward references

- Prompt 10 (release-gate) runs `scripts/train_gallodoc_embedder.py
  --mode tiny` as part of the end-to-end demo.
- The adapter is the fourth entry in
  [`gallodoc/semantic/embeddings/__init__.py`](../../gallodoc/semantic/embeddings/__init__.py)'s
  `EMBEDDING_ADAPTERS` registry, alongside `local_stub`, `bge_m3`, and
  `sentence_transformers` (Codex 05).
