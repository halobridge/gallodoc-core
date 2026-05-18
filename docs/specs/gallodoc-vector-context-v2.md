# GalloDoc Vector Context — v2.0

**Schema slug:** `gallodoc.vector_context.v2.0`
**Top-level key:** `vector_context` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#2-vector_context--native-rag)

Native RAG support. Records embedding indexes, embedding chunks (by hash),
and retrieval receipts so RAG behavior is provable from hashes and chunk
references alone — without ever exposing the vectors themselves or the
underlying chunk text.

## Shape

```json
{
  "schema_version": "gallodoc.vector_context.v2.0",
  "embedding_indexes": [],
  "embedding_chunks": [],
  "retrieval_receipts": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `EmbeddingIndex`   | `index_id`, `embedding_model_hash_or_id`, `dimensions`, `distance_metric`, `chunking_strategy`, `created_at`. |
| `EmbeddingChunk`   | `chunk_id`, `source_artifact_ref`, `source_span`, `text_hash`, `token_count`, `embedding_hash`, `model_hash_or_id`, `metadata_summary`, `created_at`. |
| `RetrievalReceipt` | `retrieval_id`, `query_hash`, `index_id`, `top_k`, `returned_count`, `selected_chunk_refs[]`, `score_summary`, `noise_flag`, `policy_outcome_ref`, `created_at`. |

## Privacy invariants

- Public envelope stores `embedding_hash`, never `raw_vector` /
  `embedding_vector` / `vector_payload` (validator rejects these keys).
- Raw chunk text is optional; if present it must be redacted/safe.
  Forbidden keys include `chunk_text` and `raw_chunk_text`.
- v1.4 `agent_observability.retrieval_traces` map directly into
  `retrieval_receipts` so the RAG path is provable across the v1.4 ↔ v2.0
  surface without re-deriving intent.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_vector_context.json`](../../examples/v2_0/gallodoc_vector_context.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
