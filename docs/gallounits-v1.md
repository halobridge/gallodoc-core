# GalloUnits v1

**Status:** open-core spec, frozen with GalloDoc Core v1.

## Purpose

A **GalloUnit** is a model-agnostic, cryptographically-stable, semantic unit
of evidence inside a GalloDoc.

> Models may tokenize differently, but they should all be able to point back
> to the same GalloUnit.

The unit is the thing humans, reviewers, certifiers, and downstream
applications reason about. The token count is something a *model* cares about
for billing and prompt sizing — not the unit of evidence itself. Keeping the
two cleanly separated lets HaloBridge:

* swap models without re-defining what a "claim" is,
* let multiple providers extract from the same document and reconcile their
  outputs by `unit_id`,
* attach human reviews, certifications, and Truth-Ledger claims to a stable
  `unit_id` that survives re-tokenization, model upgrades, and OCR re-runs,
* surface per-model token costs through `model_projections` without leaking
  raw text into the open-core envelope.

## Why GalloUnits are not model tokens

Model tokenization is provider-specific:

* OpenAI BPE tokenizers (cl100k_base, o200k_base) split differently from
  Anthropic's tokenizer, which differs again from Google's SentencePiece.
* The same paragraph turns into different token spans in every model.
* Token IDs are unstable across provider upgrades.

GalloUnits live at a layer above tokenization:

* a unit is **what the document means** (a clause, a paragraph, a table cell,
  an image region, an audio segment, a video segment),
* the unit's identity is the canonical text + position hash, not a token
  range,
* every model that processes the unit attaches a separate
  `model_projections[]` entry with its own token count.

## `unit_strategy`

Identifies the rules used to cut the document into units. v1 ships
`gallounit_v1`. New strategies (e.g. `gallounit_clause_v2`,
`gallounit_speaker_turn_v1`) land via additive entries; existing entries are
frozen.

## Unit types

```
sentence
paragraph
section
clause
table
cell
image_region
audio_segment
video_segment
entity
custom
```

* `sentence` / `paragraph` / `section` / `clause` cover textual documents
  (PDF, HTML, Markdown).
* `table` / `cell` cover tabular data (one unit per table or per cell).
* `image_region` covers bounded regions inside an image (e.g. an insurance
  card field, an OCR bounding box).
* `audio_segment` / `video_segment` cover time-bounded spans of media.
* `entity` covers extracted entities that don't map to a contiguous span
  (e.g. an aggregated patient identifier).
* `custom` is the open-core escape hatch for vendor-specific unit types.

## Semantic roles

`semantic_role` tags the *meaning* of a unit independent of its type. Examples:
`payment_terms`, `patient_identifier`, `claim_detail`, `legal_clause`,
`evidence`, `service_line`, `diagnosis_code`, `procedure_code`, `unknown`.

The semantic role is the contract between extractors and reviewers — a
contradiction or a certification refers to a role+id pair, not raw text.

## Source spans

Every unit carries a `source_span` so the reviewer can locate it:

```jsonc
"source_span": {
  "page": 3,                  // PDF / image page (1-indexed)
  "start_char": 1280,         // canonical-text character offset
  "end_char": 1410,
  "start_time_ms": null,      // audio/video only
  "end_time_ms": null,
  "region": null              // bbox / polygon for image_region / video_segment
}
```

* Text units use `page`, `start_char`, `end_char`.
* Audio segments use `start_time_ms`, `end_time_ms`.
* Video segments use `start_time_ms`, `end_time_ms`, and an optional `region`
  bbox/polygon for the spatial sub-region.
* Image regions use `page` and `region`.

The combination of `source_span` + `text_hash` is the stable identity of the
unit across re-runs.

## Text hashes

`text_hash` is a `sha256` over the canonical unit text:

* normalize whitespace,
* normalize Unicode (NFC),
* trim leading/trailing whitespace,
* hash the resulting bytes.

`gallounits.canonical_text_hash` is the `sha256` over the document's full
canonical text — the parent hash from which unit hashes derive their
guarantee of stability.

In the **open-core projection** the unit's raw text never appears. Only
`text_hash` and a bounded `content_summary` (≤512 chars, no PHI) ship publicly.
Vendors who need to round-trip raw text do so under
`extensions.<vendor>.gallounits.units[<id>].text` with their own redaction
policy.

## Model projections — the seat of token counts

Every model that processes a unit attaches one entry:

```jsonc
{
  "projection_id": "...",
  "unit_id": "gu_001",
  "provider": "openai",         // openai | anthropic | google | azure_openai | ollama | local | custom
  "model_family": "gpt-4o",
  "model": "gpt-4o-2024-08-06",
  "tokenizer": "o200k_base",
  "token_count": 142,
  "projection_hash": "sha256:...",  // sha256 over (canonical_unit_text + tokenizer)
  "created_at": "..."
}
```

Properties:

* `token_count` is the per-model count for *this unit*, not the whole document.
* `projection_hash` is recomputable: a verifier with the canonical text and
  the named tokenizer can recompute the same hash.
* Multiple projections per unit are expected — that is the whole point of
  keeping the GalloUnit stable.

## AI usage references

Every AI run against a unit tags itself in `gallounits.units[].ai_usage_refs`
with the `ai_usage.runs[].run_id` of the call. Reviewers can compute the cost
of a single semantic claim by summing `ai_usage` runs whose `run_id` appears
in the unit's `ai_usage_refs`.

## Privacy rules

Open-core projection rules for GalloUnits:

* **Never** project raw unit text. Use `text_hash` + bounded `content_summary`.
* **Never** project tokenized strings or per-token logprobs. Token counts
  only.
* **Never** project raw OCR confidence matrices, transcript timestamps with
  PHI, or spatial regions whose pixel dump would re-identify a patient.
* `extractions` (the per-unit field bag) is sanitized through
  `_strip(...)` — any subkey matching the forbidden patterns
  (`raw_prompt`, `raw_response`, `signing_key`, etc.) is dropped.
* Vendors who need privileged unit content publish it under
  `extensions.<vendor>.gallounits.*` with their own access controls.

## Media support

* **Image regions.** `unit_type = image_region`, `source_span.region` carries
  the bounding box (`{ "kind": "bbox", "x": 120, "y": 80, "w": 300, "h": 40 }`).
  An OCR-derived `content_summary` is bounded; for PHI-sensitive regions the
  summary is replaced with a placeholder and `text_hash` covers a redacted
  canonical form.
* **Audio segments.** `unit_type = audio_segment`, `source_span.start_time_ms`
  and `end_time_ms` define the span. `content_summary` is a bounded transcript
  summary; PHI tokens are redacted before the unit ships.
* **Video segments.** `unit_type = video_segment`, `source_span` carries time
  bounds plus an optional spatial `region`. Keyframes belong in the envelope
  `media.keyframes` array, not inside the unit.

## Examples

### Text unit (clause)

```jsonc
{
  "unit_id": "gu_001",
  "unit_type": "clause",
  "semantic_role": "payment_terms",
  "source_span": { "page": 3, "start_char": 1280, "end_char": 1410, "start_time_ms": null, "end_time_ms": null, "region": null },
  "text_hash": "sha256:1a2b3c...",
  "content_summary": "Net 30 payment terms for vendor renewals (synthetic).",
  "confidence": 0.93,
  "ai_usage_refs": ["run-extract-001"]
}
```

### Audio segment

```jsonc
{
  "unit_id": "gu_audio_004",
  "unit_type": "audio_segment",
  "semantic_role": "patient_identifier",
  "source_span": { "page": null, "start_char": null, "end_char": null, "start_time_ms": 12000, "end_time_ms": 18500, "region": null },
  "text_hash": "sha256:9f8e7d...",
  "content_summary": "Caller states their member id (PHI redacted in open core).",
  "confidence": 0.81
}
```

### Video segment

```jsonc
{
  "unit_id": "gu_video_002",
  "unit_type": "video_segment",
  "semantic_role": "evidence",
  "source_span": {
    "page": null, "start_char": null, "end_char": null,
    "start_time_ms": 244000, "end_time_ms": 246500,
    "region": { "kind": "bbox", "x": 320, "y": 120, "w": 480, "h": 360 }
  },
  "text_hash": "sha256:5e4d3c...",
  "content_summary": "Procedure clip — anatomical region (synthetic).",
  "confidence": 0.7
}
```

### Per-model projections

```jsonc
"model_projections": [
  { "projection_id": "p1", "unit_id": "gu_001", "provider": "openai",   "model_family": "gpt-4o",     "model": "gpt-4o-2024-08-06", "tokenizer": "o200k_base", "token_count": 142, "projection_hash": "sha256:aaa", "created_at": "..." },
  { "projection_id": "p2", "unit_id": "gu_001", "provider": "anthropic","model_family": "claude-4",   "model": "claude-opus-4-7",   "tokenizer": "anthropic_v2", "token_count": 156, "projection_hash": "sha256:bbb", "created_at": "..." },
  { "projection_id": "p3", "unit_id": "gu_001", "provider": "google",   "model_family": "gemini-1.5", "model": "gemini-1.5-pro",   "tokenizer": "sentencepiece_v2", "token_count": 138, "projection_hash": "sha256:ccc", "created_at": "..." }
]
```

Same `unit_id`, three different `token_count`s — proving the point: models may
tokenize differently, but they all point back to the same GalloUnit.
