# GalloDoc Units v1

> Models may tokenize differently, but they should all be able to point back
> to the same GalloUnit.

This page is a developer-friendly summary. The full v1 spec lives at
[`gallounits-v1.md`](gallounits-v1.md). The implementation lives in
`gallodoc.units`.

## What a GalloUnit is

A model-agnostic, cryptographically-stable, semantic unit of evidence inside
a document. Sentence, paragraph, section, clause, table, cell, image_region,
audio_segment, video_segment, entity, or `custom`.

Every unit ships with:

| Field | Meaning |
|---|---|
| `unit_id` | Stable identifier (deterministic from text hash + position). |
| `unit_type` | One of the v1 enum values. |
| `semantic_role` | Domain role (e.g. `payment_terms`, `claim_detail`). |
| `source_span` | `(page, start_char, end_char, start_time_ms, end_time_ms, region)`. |
| `text_hash` | sha256 of the canonical unit text. |
| `content_summary` | Bounded summary (≤512 chars). No PHI in open core. |
| `confidence` | 0.0–1.0. |
| `evidence_refs`, `relationship_refs`, `validation_refs`, `ai_usage_refs` | Cross-references. |
| `extractions` | Free-form extension bag (sanitized at projection). |

## Why units, not tokens?

* Tokens are provider-specific and unstable across model upgrades.
* The same paragraph yields different token counts in different providers.
* Reviewers, certifiers, and Truth-Ledger claims need a stable identifier.
* Token counts ride beside the unit under
  `gallounits.model_projections[]` — same `unit_id`, multiple tokenizers.

## Building units from text

```python
from gallodoc.units import (
    build_gallounits_block,
    compute_text_hash,
    normalize_text,
    segment_text_to_units,
)

text = open("sample.txt").read()
print(compute_text_hash(text))           # sha256:...
units = segment_text_to_units(text)      # default strategy: gallounit_v1
block = build_gallounits_block(text)     # ready to drop into envelope["gallounits"]
```

The segmenter is deterministic: same input text ⇒ same `unit_id`s and the
same `text_hash`es. Re-running on unchanged text produces an identical
block.

## Classification

Rule-based classifier (no optional dependencies required):

```python
from gallodoc.units.classifier import UnitClassifier, classify_unit

print(classify_unit("Net 30 payment terms apply."))
# {'unit_type': 'payment_terms', 'semantic_role': 'payment_terms', 'confidence': 0.92}
```

Labels covered: `heading`, `paragraph`, `clause`, `table_row`, `line_item`,
`signature_block`, `payment_terms`, `amount_block`, `date_block`,
`unknown`. The classifier exposes `classify_with_model` as an extension hook
for optional sklearn / ONNX backends; without them, the rule path is used.

## Per-model token projections

```python
from gallodoc.units import build_gallounits_block, build_model_projection

block = build_gallounits_block("Net 30 payment terms apply.")
proj_openai    = build_model_projection(block["units"], provider="openai",    model="gpt-4o-2024-08-06")
proj_anthropic = build_model_projection(block["units"], provider="anthropic", model="claude-opus-4-7")
```

Default token estimator is the deterministic char-count heuristic
(`ceil(len(text) / 4)`). Install the optional `tokenizer` extra
(`pip install gallodoc[tokenizer]`) to use exact OpenAI tokenizers via
`tiktoken`. Custom providers can register through:

```python
from gallodoc.units.projections import register_token_estimator
register_token_estimator("custom", "magic", lambda t, p, m: my_count(t))
```

## Privacy invariants

* Raw unit text is **never** projected to open core. Only `text_hash` and a
  bounded `content_summary` survive.
* Token IDs and per-token logprobs are never carried — token *counts* only.
* Vendors who need privileged unit content publish it under
  `extensions.<vendor>.gallounits.*` with their own access controls.

## CLI

```bash
gallodoc units sample.txt
gallodoc units sample.txt --json
gallodoc units sample.txt --json --no-classify   # skip the rule classifier
```

## Acceptance properties

* `unit_id`s are unique per document.
* `text_hash` is stable across whitespace and Unicode normalization.
* The same input text always produces the same projection hashes per
  `(provider, model, tokenizer)` triple.
