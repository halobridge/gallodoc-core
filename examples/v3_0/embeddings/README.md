# `examples/v3_0/embeddings/` — open embeddings adapter walkthroughs

These four examples exercise the Codex 05 surface end-to-end:

1. The default `local_stub` adapter produces a v3 envelope with
   `gallounits.embeddings[]` populated.
2. The `--include-vector` opt-in flag is exercised against an envelope
   that declares `safety_profile.raw_vectors_stored = true`.

Spec: [`docs/specs/gallodoc-core-v3-embeddings.md`](../../../docs/specs/gallodoc-core-v3-embeddings.md).

All examples are **synthetic** — no PHI, no real customer data, no
real tenant IDs.

## Files

| File | What it demonstrates |
|---|---|
| `input_envelope.json` | A v3 envelope with 3 GalloUnits, each carrying `content_summary` and `text_hash`. No `safety_profile`. |
| `output_envelope.gdoc.json` | Result of `apply_embeddings(input, LocalStubEmbeddingAdapter(), "document_summary_embedding")`. `gallounits.embeddings[]` populated with 3 entries; **no** `raw_vector` fields. |
| `input_envelope_with_raw_vectors_authorized.json` | Same as `input_envelope.json` but with `safety_profile.raw_vectors_stored = true`. |
| `output_envelope_with_raw_vectors.gdoc.json` | Result with `include_vector=True`. Each embedding carries a `raw_vector` field of 32 floats (the `local_stub` dimension). |

## Reproduce

From the package root:

```bash
gallodoc semantic embed \
  examples/v3_0/embeddings/input_envelope.json \
  --adapter local_stub \
  --purpose document_summary_embedding \
  --out /tmp/output_envelope.gdoc.json
```

With raw vectors:

```bash
gallodoc semantic embed \
  examples/v3_0/embeddings/input_envelope_with_raw_vectors_authorized.json \
  --adapter local_stub \
  --purpose document_summary_embedding \
  --include-vector \
  --out /tmp/output_envelope_with_raw_vectors.gdoc.json
```

Without `safety_profile.raw_vectors_stored = true`, the second command
returns a non-zero exit code and writes nothing — try it on the first
input to see the safety gate fire.

## What's in `gallounits.embeddings[]`

Each entry has the documented shape:

```json
{
  "embedding_id": "emb_…",
  "unit_id": "gu_summary",
  "model_id": "gallodoc.embedder.local_stub.v3.0",
  "model_hash_or_id": "sha256:…",
  "dimensions": 32,
  "vector_ref": "opaque://store/emb_…",
  "embedding_hash": "sha256:…",
  "purpose": "document_summary_embedding",
  "created_at": "2026-05-…Z"
}
```

The output with `--include-vector` additionally carries a `raw_vector`
field — the 32 floats produced by the `local_stub` adapter. The vector
is deterministic (same `content_summary` → same vector) so the example
is reproducible from this README without re-recording fixtures.

## Why `local_stub`?

`local_stub` is the default precisely because it has no external
dependencies. The vectors are cryptographic noise — they are NOT
semantic embeddings — so production retrieval should use `bge_m3`
(`pip install gallodoc[semantic]`) or a `sentence_transformers` model
of your choice. The CLI flags are identical:

```bash
gallodoc semantic embed input.json --adapter bge_m3 --out output.json
```

## Determinism

The `local_stub` adapter is deterministic on `content_summary` only —
**timestamps (`created_at`) vary per run**. Tests that diff the example
output stabilize that field. See
`tests/v3_0/semantic/embeddings/test_embedding_examples.py`.
