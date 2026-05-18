# GalloDoc Core — Spec Index

Index of the public specs that ship in this repository.

## Active spec family

| Spec | Status | Notes |
|---|---|---|
| [`gallodoc-core-v3-master-spec.md`](gallodoc-core-v3-master-spec.md) | **active** | The Portable Operational Intelligence Document Standard. 18 required + 23 optional top-level sections. New consumers default to v3. |
| [`gallodoc-core-v3-reference-projector.md`](gallodoc-core-v3-reference-projector.md) | **active** | Open-source reference projector + v1→v3 migration helper. Closes the largest open-source adoption gap by shipping a sanitizer that third-party producers no longer have to re-implement. Concurrently fixes the Q5 double-emission bug. |
| [`gallodoc-core-v3-connector-sdk.md`](gallodoc-core-v3-connector-sdk.md) | **active** | Open connector SDK — `gallodoc.connectors` base interfaces, five starter connectors (`generic_json`, `csv_row`, `pdf_file_metadata`, `salesforce_account_stub`, `invoice_stub`), and the `gallodoc connector convert` CLI. Closes the "5-minute install + first envelope" gap. |
| [`gallodoc-core-v3-linker.md`](gallodoc-core-v3-linker.md) | **active** | GalloUnit-keyed deterministic linker (Codex 04). Writes `relationships.relationships[]` entries with `status: "suggested"` + `discovered_by: "gallodoc-linker/3.0.0"` (Decision 3). Reads cryptographic anchors + author-asserted `::semantic_intent` (Decision 5). |
| [`gallodoc-core-v3-embeddings.md`](gallodoc-core-v3-embeddings.md) | **active** | Open embeddings adapter interface (Codex 05). Attaches embeddings to `gallounits.embeddings[]`. Three starter adapters (`local_stub`, `bge_m3`, `sentence_transformers`); heavy ones lazy-imported behind `[semantic]` extra. Raw vectors never ship by default — `--include-vector` requires `safety_profile.raw_vectors_stored == true`. |
| [`gallodoc-core-v3-training-lab.md`](gallodoc-core-v3-training-lab.md) | **active** | Embedder training lab (Codex 06). Open-source. Turns human-curated v3 envelopes into a JSONL training set the prompt 07 embedder consumes. Linker-discovered + human-confirmed pairs (Decision 3) are included as positives. Four deterministic hard-negative strategies. Deterministic seeded train/dev/test split. Every pair passes `assert_no_enterprise_leakage` — no skip path. |
| [`gallodoc-core-v3-trained-embedder.md`](gallodoc-core-v3-trained-embedder.md) | **active** | Trained embedder v1 recipe (Codex 07). Ships the training recipe + evaluation harness + lazy-load adapter shell for `gallodoc-bge-m3-v1`. **No model weights committed** — recipe-only release. Six purpose heads (LoRA on frozen `BAAI/bge-m3`). Decision 5 filter: positives require resolved `semantic_intent` on both source and target units. |
| [`gallodoc-core-v3-federation.md`](gallodoc-core-v3-federation.md) | **active** | Optional top-level `federation` block (Codex 08). Carries cross-tenant matching policy + matching receipts. Most-restrictive-intersection-wins enforcement. Per Decision 4: first-class top-level block, never under `extensions.halobridge.*`. `raw_data_exposed` is `false` in v3.0 — receipts carry hashes and refs only. |
| [`gallodoc-semantic-intent-v3.md`](gallodoc-semantic-intent-v3.md) | **active** | Starter vocabulary for `gallounits.units[].semantic_intent`. Authored via the `::semantic_intent` GalloMarkdown block (Decision 5). Extends additively in minor releases. |
| [`gallodoc-core-v3-aibi-planner.md`](gallodoc-core-v3-aibi-planner.md) | **active** | NL → GQL planner (Codex 09). Deterministic template-based planner emits `QueryPlan` objects targeting the v2.0 `query_access` (GQL) grammar. Closed enums: 5 `safe_query_type` values, 6 `filter.op` primitives. No raw SQL ever. Decision-aware — flat trust paths (D2), `relationship_status: confirmed` default (D3), federation_intersection scopes derived from source envelope (D4). Planner only — an executor is out of scope for v3.0. |

## Legacy spec family (parallel-supported)

| Spec | Status | Notes |
|---|---|---|
| [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md) | superseded by v3 | v2.0 added 11 optional platform blocks on top of the `gallodoc-core/v1` envelope identifier. Validates under the parallel v1 validator. |
| [`gallodoc-core-v1.6-agent-supply-chain-security.md`](gallodoc-core-v1.6-agent-supply-chain-security.md) | superseded by v3 | v1.6 amendment. Block stays optional in v3 at top level. |
| [`gallodoc-core-v1.5-trust-decision.md`](gallodoc-core-v1.5-trust-decision.md) | superseded by v3 | v1.5 amendment. **Consolidated into the v3 required `trust` block.** |
| [`gallodoc-core-v1.4-agent-observability.md`](gallodoc-core-v1.4-agent-observability.md) | superseded by v3 | v1.4 amendment. Block stays optional in v3 at top level. |
| [`gallodoc-core-v1.3-residency-training-model-risk.md`](gallodoc-core-v1.3-residency-training-model-risk.md) | superseded by v3 | v1.3 amendments. Blocks stay optional in v3 at top level. |
| [`gallodoc-core-v1.2-consent-custody-attestation.md`](gallodoc-core-v1.2-consent-custody-attestation.md) | superseded by v3 | v1.2 amendments. Blocks stay optional in v3 at top level. |
| [`gallodoc-core-v1.1-execution-governance.md`](gallodoc-core-v1.1-execution-governance.md) | superseded by v3 | v1.1 amendment. Block stays optional in v3 at top level. |
| [`GALLODOC_CORE_V1_FROZEN.md`](../GALLODOC_CORE_V1_FROZEN.md) | superseded by v3 | v1 base. Carries a "Superseded by v3" preamble; v1 stays parallel-supported for a 6-month deprecation window beginning 2026-05-16. |

## Companion specs

| Spec | Status |
|---|---|
| [`gallodoc-query-language-v2.md`](gallodoc-query-language-v2.md) | v2.0 — still current |
| [`gallodoc-vector-context-v2.md`](gallodoc-vector-context-v2.md) | v2.0 — still current |
| [`gallodoc-document-relationships-v2.md`](gallodoc-document-relationships-v2.md) | superseded by v3 `relationships` |
| [`gallodoc-temporal-versions-v2.md`](gallodoc-temporal-versions-v2.md) | v2.0 — still current |
| [`gallodoc-policy-governance-v2.md`](gallodoc-policy-governance-v2.md) | v2.0 — still current |
| [`gallodoc-access-control-v2.md`](gallodoc-access-control-v2.md) | v2.0 — still current |
| [`gallodoc-human-review-v2.md`](gallodoc-human-review-v2.md) | v2.0 — still current |
| [`gallodoc-workflow-execution-v2.md`](gallodoc-workflow-execution-v2.md) | v2.0 — still current |
| [`gallodoc-connector-lineage-v2.md`](gallodoc-connector-lineage-v2.md) | superseded by v3 `source.connector_lineage` |
| [`gallodoc-compute-trace-v2.md`](gallodoc-compute-trace-v2.md) | v2.0 — still current |
| [`gallodoc-artifact-bom-v2.md`](gallodoc-artifact-bom-v2.md) | v2.0 — still current |
| [`gallomarkdown-v1.md`](gallomarkdown-v1.md) | v1 — still current |
