# Semantic encoder guide

**Audience:** developers attaching embeddings to v3 envelopes — adapter
plug-ins, embedding pipelines, downstream consumers of
`gallounits.embeddings[]`.
**Reading time:** ~6 minutes.
**Companion specs:**
[`docs/specs/gallodoc-core-v3-embeddings.md`](../specs/gallodoc-core-v3-embeddings.md),
[`docs/specs/gallodoc-core-v3-training-lab.md`](../specs/gallodoc-core-v3-training-lab.md),
[`docs/specs/gallodoc-core-v3-trained-embedder.md`](../specs/gallodoc-core-v3-trained-embedder.md).

---

## The embedding pipeline at a glance

```
GalloUnit -> EmbeddingAdapter -> EmbeddingRecord -> gallounits.embeddings[]
```

Each GalloUnit (a text / image / audio chunk inside an envelope's
`gallounits.units[]`) can have one or more embeddings attached. The
adapter abstraction means consumers can swap between `local_stub` (the
deterministic default), `bge_m3` (the open-weights BGE-M3 model),
`sentence_transformers` (anything HuggingFace), or
`gallodoc_bge_m3_v1` (the trained model — see
[`training-guide.md`](training-guide.md)).

---

## The 5-minute path

```bash
# 1. Build an envelope with GalloUnits.
gallodoc connector convert --connector generic_json --input my.json --out env.gdoc.json

# 2. Attach embeddings.
gallodoc semantic embed env.gdoc.json \
  --adapter local_stub \
  --purpose document_retrieval \
  --out env_with_embeddings.gdoc.json

# 3. Validate.
gallodoc validate env_with_embeddings.gdoc.json
```

`local_stub` is deterministic and ships in core (zero extra dependencies).
For real embeddings:

```bash
pip install gallodoc[semantic]
gallodoc semantic embed env.gdoc.json --adapter bge_m3 --purpose document_retrieval
```

---

## The four adapter slugs

| Slug | Install | What it does |
|---|---|---|
| `local_stub` | core (default) | Deterministic stub. Suitable for tests + CI. Vectors are non-semantic placeholders. |
| `bge_m3` | `pip install gallodoc[semantic]` | `BAAI/bge-m3`. Open weights. Multilingual. |
| `sentence_transformers` | `pip install gallodoc[semantic]` | Any sentence-transformers model. Configure via `--model`. |
| `gallodoc_bge_m3_v1` | weights via env var | The trained GalloDoc embedder. See [`training-guide.md`](training-guide.md). |

---

## The 6-value `PURPOSE_ENUM`

Embedding records carry a `purpose` value declaring what task they were
generated for:

```
document_retrieval | semantic_similarity | relationship_match |
intent_match | role_match | clustering
```

The closed enum lets downstream consumers filter without re-running the
embedder. The trained `gallodoc-bge-m3-v1` model has 6 heads, one per
purpose.

---

## Where embeddings live in the envelope

```json
{
  "gallounits": {
    "units": [
      {
        "unit_id": "u-1",
        "text_hash": "...",
        "semantic_role": "invoice_line_item",
        "semantic_intent": "invoice_to_employee_approver"
      }
    ],
    "embeddings": [
      {
        "embedding_id": "emb-1",
        "unit_id": "u-1",
        "adapter": "bge_m3",
        "purpose": "relationship_match",
        "dim": 1024,
        "vector_hash": "...",
        "generated_at": "2026-05-17T12:00:00Z"
      }
    ]
  }
}
```

**Embeddings are a sibling array under `gallounits`** — NOT a separate
top-level block. This was a deliberate design choice (see
[`docs/specs/gallodoc-core-v3-embeddings.md §2`](../specs/gallodoc-core-v3-embeddings.md))
to keep retrieval co-located with the unit it indexes.

---

## Raw vectors do not ship by default

`EmbeddingRecord.vector` is `None` unless the producer opts in. The
envelope ships only `vector_hash` (a deterministic hash of the vector
bytes) + `dim` + `adapter` + `purpose`.

To include raw floats, two conditions must both hold:

1. The envelope's `safety_profile.raw_vectors_stored` is `true`.
2. The producer passes `--include-vector` to
   `gallodoc semantic embed`.

If either is missing, `EnterpriseLeakageError` is raised. The release
safety gate (check #5) refuses to pass if raw vectors leak through.

---

## Writing your own adapter

Implement `gallodoc.semantic.embeddings.EmbeddingAdapter`:

```python
from gallodoc.semantic.embeddings import (
    EmbeddingAdapter,
    EmbeddingRecord,
    PURPOSE_ENUM,
)


class MyAdapter(EmbeddingAdapter):
    slug = "my_adapter"
    purpose_default = "document_retrieval"

    def available(self) -> bool:
        """Return True if all dependencies + weights are present."""
        ...

    def embed(self, text: str, *, purpose: str) -> EmbeddingRecord:
        assert purpose in PURPOSE_ENUM
        vector = ...  # call your model
        return EmbeddingRecord(
            adapter=self.slug,
            purpose=purpose,
            dim=len(vector),
            vector_hash=self.hash_vector(vector),
            vector=None,  # default: do not ship raw bytes
        )
```

Register your adapter in
`gallodoc.semantic.embeddings.EMBEDDING_ADAPTERS` so the CLI picks it
up.

---

## Adapter selection guidance

| Need | Adapter |
|---|---|
| Unit tests / CI / quick sanity check | `local_stub` |
| General-purpose multilingual retrieval | `bge_m3` |
| Custom sentence-transformers model | `sentence_transformers` with `--model` |
| GalloDoc-tuned relationship inference | `gallodoc_bge_m3_v1` |

---

## Further reading

- Spec: [`docs/specs/gallodoc-core-v3-embeddings.md`](../specs/gallodoc-core-v3-embeddings.md).
- Training the GalloDoc adapter:
  [`docs/specs/gallodoc-core-v3-training-lab.md`](../specs/gallodoc-core-v3-training-lab.md)
  and [`docs/specs/gallodoc-core-v3-trained-embedder.md`](../specs/gallodoc-core-v3-trained-embedder.md).
- Audience-targeted training guide:
  [`training-guide.md`](training-guide.md).
- Linker (which reads embeddings as a signal):
  [`linker-guide.md`](linker-guide.md).
