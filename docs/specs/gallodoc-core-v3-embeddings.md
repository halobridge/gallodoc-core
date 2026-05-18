# GalloDoc Core v3 — GalloUnit embeddings adapter

**Status:** active. Ships in v3.0.0 alongside Codex 03 (connector SDK) and Codex 04 (linker).
**Schema family:** `gallodoc-core/v3`.
**Optional install:** `pip install "gallodoc[semantic]"` (only required for the
heavy adapters — `bge_m3`, `sentence_transformers`).

This spec defines the open embeddings adapter interface, the storage shape
of `gallounits.embeddings[]`, the privacy posture, and the CLI surface
(`gallodoc semantic embed`). It is locked against the five anchor decisions
in [../../../docs/v3-design/07_decisions.md](../../../docs/v3-design/07_decisions.md)
and reads from prompt [05_gallounit_embeddings.md](../../../docs/v3-design/06_codex_prompts_draft/05_gallounit_embeddings.md).

---

## 1. Overview

Embeddings attach to GalloUnits — the canonical, model-agnostic semantic
anchors in the v3 envelope — as a sibling array under `gallounits`:
`gallounits.embeddings[]`. They are NOT a new top-level block.

Why sibling-of-units rather than a new top-level block:

- GalloUnits are the natural semantic anchor (`unit_id` + `text_hash`
  survive re-tokenization). An embedding always attaches to a GalloUnit;
  putting them next to the unit array keeps the relationship cheap to
  enforce structurally (`unit_id` resolves against `gallounits.units[]`
  in the same block).
- A new top-level block would parallel `vector_context` (v2.0) and force
  consumers to choose between two semantic surfaces. `vector_context`
  exists for RAG-retrieval chunks — a different semantic level —
  and both can coexist.

The v2.0 `vector_context` block stays as-is for RAG retrieval chunks
(see [`gallodoc-vector-context-v2.md`](gallodoc-vector-context-v2.md)).

---

## 2. Privacy posture

**Raw vector floats NEVER ship by default.** The default storage shape
records only metadata + a deterministic hash + an opaque ref:

```json
{
  "embedding_id": "emb_3f1a9e4c8e2b5d04",
  "unit_id": "gu_invoice_total",
  "model_id": "gallodoc.embedder.local_stub.v3.0",
  "model_hash_or_id": "sha256:…",
  "dimensions": 32,
  "vector_ref": "opaque://store/emb_3f1a9e4c8e2b5d04",
  "embedding_hash": "sha256:…",
  "purpose": "document_summary_embedding",
  "created_at": "2026-05-16T12:00:00Z"
}
```

- `embedding_id` — deterministic ID derived from
  `sha256(unit_id::purpose::adapter.model_id)[:16]`, prefixed `emb_`.
- `unit_id` — MUST resolve to a `gallounits.units[].unit_id` in the
  same envelope.
- `model_id` — opaque adapter model identifier (e.g.
  `"gallodoc.embedder.local_stub.v3.0"`, `"BAAI/bge-m3"`,
  `"sentence_transformers:all-MiniLM-L6-v2"`).
- `model_hash_or_id` — `sha256:<hex>` over the model_id (or a real model
  weight hash if known). The platform projector can replace this with a
  cryptographic hash of the actual model weights when available.
- `dimensions` — embedding dimensions (integer ≥ 1).
- `vector_ref` — opaque reference (e.g. `opaque://store/<embedding_id>`).
  Consumers store the actual vector in their own infrastructure.
- `embedding_hash` — SHA-256 of the canonical-serialized vector. Same
  input vector → same hash; allows downstream consumers to detect
  vector drift without ever reading the vector.
- `purpose` — one of the closed `PURPOSE_ENUM` values (§4).
- `created_at` — RFC 3339 UTC.

### The `--include-vector` opt-in

The CLI accepts an `--include-vector` flag that ships the raw vector
inline (`raw_vector: list[float]`) in each embedding record. The flag
raises `gallodoc.projection.safety.EnterpriseLeakageError` unless the
input envelope declares the producer's intent explicitly:

```json
{
  "safety_profile": { "raw_vectors_stored": true }
}
```

Default (missing / `false`) → `--include-vector` is rejected.

Even when authorized, `raw_vector` is the only field that ships beyond
the hash + ref metadata. Adapter weights, prompts, and any other model
internals stay out of the envelope.

---

## 3. The `EmbeddingAdapter` interface

```python
class EmbeddingAdapter(ABC):
    slug: str          # stable adapter identifier ("local_stub", "bge_m3", "sentence_transformers")
    version: str       # adapter version (semver)
    model_id: str      # opaque model identifier the adapter uses
    dimensions: int    # embedding dimensions

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text. Never raises on empty input
        (`embed([])` → `[]`).
        """

    @classmethod
    def available(cls) -> bool:
        """True iff the adapter's optional dependencies are importable.
        Heavy adapters that need extras must implement this so the CLI
        can decide whether to surface them in --help / error messages."""
        return True
```

`available()` is a class method so the CLI can check support without
constructing the adapter (and therefore without paying the lazy-import
cost). Adapters that need extras override it; `local_stub` keeps the
default `True`.

`embed(texts)` is the single hot-path method. It never raises on empty
input — callers can use `adapter.embed([])` to probe the adapter without
loading a model.

### The `EmbeddingRecord` dataclass

```python
@dataclass
class EmbeddingRecord:
    embedding_id: str
    unit_id: str
    model_id: str
    model_hash_or_id: str
    dimensions: int
    vector_ref: str           # opaque, e.g. "opaque://store/<id>"
    embedding_hash: str        # sha256:<hex>
    purpose: str               # from PURPOSE_ENUM
    created_at: str            # RFC 3339 UTC
    raw_vector: list[float] | None = None

    def to_dict(self) -> dict[str, Any]: ...
```

`to_dict()` omits `raw_vector` entirely unless explicitly populated. This
keeps the default storage shape clean and means the privacy posture is
enforced at the serialization layer, not just at the projector.

---

## 4. The closed `PURPOSE_ENUM`

```python
PURPOSE_ENUM = frozenset({
    "document_summary_embedding",
    "relationship_embedding",
    "entity_context_embedding",
    "workflow_context_embedding",
    "risk_context_embedding",
    "policy_context_embedding",
})
```

| Purpose | Meaning |
|---|---|
| `document_summary_embedding` | Embedding represents the document's overall summary. One per `gallounits.units[]` entry that carries `content_summary`. The default in `gallodoc semantic embed`. |
| `relationship_embedding` | Embedding represents the semantics of a proposed relationship. Used by Codex 06 (training lab) + Codex 07 (trained embedder) to learn `semantic_intent` (Decision 5). |
| `entity_context_embedding` | Embedding represents the context of a named entity (`unit_type: "entity"`). |
| `workflow_context_embedding` | Embedding represents the context of a workflow step or lifecycle stage. |
| `risk_context_embedding` | Embedding represents the context of a risk signal — typically a `trust.blockers[]` entry. |
| `policy_context_embedding` | Embedding represents the context of a policy outcome or governance receipt. |

The enum is **closed** in v3.0. New purposes ship via additive v3.x
amendment — extending the enum without renaming existing values is
backward-compatible.

`apply_embeddings(..., purpose=...)` validates against this enum and
raises `ValueError` on unknown values.

---

## 5. The starter adapters

Codex 05 ships three open adapters (`local_stub`, `bge_m3`,
`sentence_transformers`). Codex 07 adds a fourth slug,
`gallodoc_bge_m3_v1`, as the lazy-load shell for the trained embedder.
The trained adapter is recipe-only — without
`GALLODOC_BGE_M3_V1_WEIGHTS` (or an explicit `weights_path`),
`available()` returns `False` and `embed()` raises a `RuntimeError`
pointing users at `scripts/train_gallodoc_embedder.py`. See
[`gallodoc-core-v3-trained-embedder.md`](gallodoc-core-v3-trained-embedder.md)
for the full recipe.

### The three Codex-05 starter adapters

### `local_stub` — default, no extras

- **Slug:** `local_stub`
- **Model id:** `gallodoc.embedder.local_stub.v3.0`
- **Dimensions:** 32
- **Determinism:** same input text → same vector. SHA-256(text) is
  reinterpreted as 32 little-endian `float32` values; the result is
  normalized so `|v_i| ≤ 1.0`.
- **Empty string:** all-zeros (32 zeros).
- **Use cases:** tests, CI, environments without an installed embedding
  model. Never call this for production retrieval — the vectors are
  cryptographic noise, not semantic embeddings.

`LocalStubEmbeddingAdapter.available()` returns `True` (no extras
required).

### `bge_m3` — `BAAI/bge-m3` via FlagEmbedding / sentence-transformers

- **Slug:** `bge_m3`
- **Model id:** `BAAI/bge-m3`
- **Dimensions:** 1024
- **Extras:** `pip install "gallodoc[semantic]"`. Lazy-imports
  `FlagEmbedding.BGEM3FlagModel`; falls back to
  `sentence_transformers.SentenceTransformer("BAAI/bge-m3")` if
  FlagEmbedding is not available.
- `BgeM3EmbeddingAdapter.available()` returns `True` iff either
  `FlagEmbedding` or `sentence_transformers` can be imported.
- Calling `.embed(texts)` without either installed raises `ImportError`
  with the message `pip install gallodoc[semantic]`.

### `sentence_transformers` — generic ST wrapper

- **Slug:** `sentence_transformers`
- **Constructor:** `SentenceTransformersEmbeddingAdapter(model_name, device="cpu")`.
- **Model id:** `f"sentence_transformers:{model_name}"`.
- **Dimensions:** resolved on first call to `embed()`.
- **Extras:** `pip install "gallodoc[semantic]"`. Lazy-imports
  `sentence_transformers.SentenceTransformer`.
- `available()` returns `True` iff `sentence_transformers` can be imported.
- Default model in tests is `"all-MiniLM-L6-v2"` (small, fast, 384 dims),
  but the adapter is generic — any ST model identifier works.

---

## 6. The `[semantic]` optional install

```toml
[project.optional-dependencies]
semantic = [
  "sentence-transformers>=2.2",
  "numpy>=1.24",
]
```

`FlagEmbedding` is **not** in the extra by default — the `bge_m3`
adapter is happy with `sentence_transformers` as a backend and the
FlagEmbedding wheel is heavier than most consumers want. Users who
prefer the FlagEmbedding path can install it explicitly.

Core's hard-dependency set is unchanged (`dependencies = []` in
`pyproject.toml`). All embedding adapters that need extras lazy-import
their dependencies inside `embed()`.

---

## 7. CLI: `gallodoc semantic embed`

```
gallodoc semantic embed <input> \
  --adapter <name> \
  --purpose <enum> \
  --out <output> \
  [--include-vector]
```

- `<input>` — path to a v3 envelope JSON file.
- `--adapter` — adapter slug. Defaults to `local_stub`.
- `--purpose` — one of `PURPOSE_ENUM`. Defaults to
  `document_summary_embedding`.
- `--out` — path to write the modified envelope JSON file.
- `--include-vector` — opt-in to ship raw vectors. Fails with non-zero
  exit code unless the input envelope's
  `safety_profile.raw_vectors_stored == true`.

Exit codes:
- `0` — success.
- non-zero — bad adapter slug, bad purpose, missing input file, write
  error, or `--include-vector` without authorization.

The CLI dispatches by the `EMBEDDING_ADAPTERS` registry:

```python
EMBEDDING_ADAPTERS: dict[str, type[EmbeddingAdapter]] = {
    "local_stub": LocalStubEmbeddingAdapter,
    "bge_m3": BgeM3EmbeddingAdapter,
    "sentence_transformers": SentenceTransformersEmbeddingAdapter,
}
```

---

## 8. The `gallounits.embeddings[]` entry shape

Full v3 shape, with every required field:

```json
{
  "embedding_id": "emb_3f1a9e4c8e2b5d04",
  "unit_id": "gu_invoice_total",
  "model_id": "gallodoc.embedder.local_stub.v3.0",
  "model_hash_or_id": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "dimensions": 32,
  "vector_ref": "opaque://store/emb_3f1a9e4c8e2b5d04",
  "embedding_hash": "sha256:5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9",
  "purpose": "document_summary_embedding",
  "created_at": "2026-05-16T12:00:00Z"
}
```

When `--include-vector` is authorized, the record gains a `raw_vector`
field:

```json
{
  "raw_vector": [0.123, -0.456, ...]
}
```

`raw_vector` length always matches `dimensions`.

---

## 9. `apply_embeddings(envelope, adapter, purpose, *, include_vector=False)`

The single envelope-integration entry point:

```python
def apply_embeddings(
    envelope: dict,
    adapter: EmbeddingAdapter,
    purpose: str,
    *,
    include_vector: bool = False,
) -> dict:
    """Attach embeddings to `gallounits.embeddings[]`. Returns the
    modified envelope. Idempotent — re-running with the same
    (adapter, purpose) appends only NEW embeddings.
    """
```

Contract:

1. Validates `purpose` against `PURPOSE_ENUM` (raises `ValueError` on
   unknown).
2. Reads `gallounits.units[]`. For each unit with a `content_summary`
   (the embedding source text), generates an embedding via
   `adapter.embed([content_summary])`.
3. Appends one `EmbeddingRecord` per unit to `gallounits.embeddings[]`.
4. Idempotent: skips units whose deterministic `embedding_id` already
   exists in `gallounits.embeddings[]` for the same adapter + purpose.
5. If `include_vector=True`, raises `EnterpriseLeakageError` unless
   `envelope["safety_profile"]["raw_vectors_stored"] == True`. When
   authorized, populates `raw_vector` on each record.
6. Calls `project_to_open_core` on the input envelope BEFORE attaching
   embeddings so the output structurally matches v3 (forbidden keys
   stripped, banned halobridge keys removed, schema_version set). The
   attached embeddings themselves are NOT re-projected — projection
   would strip `raw_vector` when authorized.

---

## 10. Forward references

- **Codex 06 — Embedder training lab.** Consumes envelopes that have
  passed through `apply_embeddings`. Training pairs are extracted from
  `gallounits.embeddings[]` + `relationships.relationships[]` with
  `status: "confirmed"`.
- **Codex 07 — GalloDoc-trained embedder.** Implements
  `EmbeddingAdapter` for the in-house model. Uses `semantic_intent`
  (Decision 5) as a learning target alongside the v2.0 `relationship_type`
  enum.

---

## 11. Open questions (deferred to v3.x)

1. Should `--include-vector` also accept a per-purpose policy (e.g.
   "raw vectors OK for `entity_context_embedding` but not
   `risk_context_embedding`")? Today the gate is envelope-wide. Defer
   until a real consumer requests purpose-level granularity.
2. Should the projector strip `gallounits.embeddings[*].raw_vector`
   unconditionally? Currently `apply_embeddings` calls the projector on
   the input only, leaving `raw_vector` intact on output when authorized.
   The platform projector can layer on top if it wants stricter
   behavior. Revisit if the open-source default needs to be tightened.
3. Cross-reference between `gallounits.embeddings[]` and
   `vector_context.embedding_chunks[]`? Not in v3.0; defer.
