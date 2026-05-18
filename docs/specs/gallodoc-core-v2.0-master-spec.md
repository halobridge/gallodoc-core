# GalloDoc Core v2.0 — Master Spec

**Status:** release candidate
**Python package version:** `2.0.0`
**Schema family:** `gallodoc-core/v1` (unchanged — frozen base)
**v2.0 introduces optional, additive top-level blocks. Every block is opt-in.**

GalloDoc Core v2.0 is the consolidated trusted-AI document/data standard. It
collects the v1.0 traceable envelope and the v1.1–v1.6 amendments, then adds
the platform primitives that every customer kept rebuilding: a safe query
language, native RAG, cross-document relationships, temporal versioning, a
portable policy/rule layer, access control with masking, human review,
workflow execution, connector lineage, a unified compute trace, and a
software bill-of-materials for referenced packages.

> **v2.0 does not break v1.x.** Every v1.x example still validates. Every
> v1.x optional block keeps its current shape. The schema family identifier
> on the envelope stays `gallodoc-core/v1`. The "2.0" name refers to the
> Python package and the consolidated standard; the on-the-wire envelope
> identifier is preserved for full backward compatibility.

## Why 2.0

GalloDoc 1.0–1.6 turned individual documents into traceable, governable,
observable, trust-aware artifacts. v2.0 makes the *platform layer* explicit:

| Track   | Theme                                       |
|---------|---------------------------------------------|
| v1.0    | Traceable Document Envelope                 |
| v1.1    | Execution Governance                        |
| v1.2    | Consent, Custody, Attestation               |
| v1.3    | Residency, Training Permission, Model Risk  |
| v1.4    | Agent Observability                         |
| v1.5    | Trust Score, Decision Gates                 |
| v1.6    | Agent Supply Chain Security                 |
| **2.0** | **Query · Vector · Relationships · Versioning · Policy · Access · Human Review · Workflow · Connector Lineage · Compute Trace · Artifact BOM** |

## Compatibility rules

1. **Envelope identifier unchanged.** The required top-level
   `schema_version` field on every GalloDoc envelope still equals
   `gallodoc-core/v1`.
2. **No removals.** v1.0–v1.6 sections keep the same field names and
   semantics. Validators built for v1.x continue to accept v2.0 envelopes.
3. **Additive only.** Every v2.0 block is an optional new top-level key.
   Older consumers ignore unknown keys.
4. **Privacy invariants preserved.** Every v2.0 block stores hashes,
   opaque references, role names, status enums, score ranges, safe
   summaries, and timestamps — never the forbidden subtree categories
   from v1.x. The `gallodoc.validation` validator and the
   `scripts/release_safety_scan.py` allowlist enforce hygiene.
5. **Per-block versioning.** Every v2.0 block's own `schema_version`
   is namespaced under `gallodoc.<block>.v2.0` so later minor versions of
   a single block can land independently.
6. **Numeric ranges.** All score / confidence ranges use the v1.x
   conventions: `risk_score` and Trust Score components in 0–100,
   `confidence` in 0–1, `malicious_likelihood` in 0–1.

## v2.0 block catalog

| Top-level key             | Slug                                       | Purpose |
|---------------------------|--------------------------------------------|---------|
| `query_access`            | `gallodoc.query_access.v2.0`               | GalloDoc Query Language (GQL) — saved queries, query receipts, query permissions. |
| `vector_context`          | `gallodoc.vector_context.v2.0`             | Native RAG — embedding indexes, embedding chunks, retrieval receipts. |
| `document_relationships`  | `gallodoc.document_relationships.v2.0`     | First-class cross-document edges — relationships, evidence, decisions. |
| `temporal_versions`       | `gallodoc.temporal_versions.v2.0`          | Versioning + replay — versions, change events, replay receipts. |
| `policy_governance`       | `gallodoc.policy_governance.v2.0`          | Portable policy/rule representation (OPA/Rego-compatible) — policy sets, rules, evaluations. |
| `access_control`          | `gallodoc.access_control.v2.0`             | Roles, permissions, masking rules, access receipts. |
| `human_review`            | `gallodoc.human_review.v2.0`               | HIM-C-style review queues, actions, outcomes. |
| `workflow_execution`      | `gallodoc.workflow_execution.v2.0`         | Pipelines + steps + artifacts as a projection of lifecycle / app runs. |
| `connector_lineage`       | `gallodoc.connector_lineage.v2.0`          | Connector sources, sync runs, record receipts. |
| `compute_trace`           | `gallodoc.compute_trace.v2.0`              | Unified spans / metrics / logs across AI, tools, scanners, workflows. |
| `artifact_bom`            | `gallodoc.artifact_bom.v2.0`               | Software / artifact bill-of-materials for referenced packages. |

Each block lives at the top level of the envelope:

```json
{
  "schema_version": "gallodoc-core/v1",
  "identity":  { ... },
  "source":    { ... },
  "purpose":   { ... },
  "lifecycle": { ... },
  "activity":  { ... },

  "execution_governance":         { "schema_version": "gallodoc.execution_governance.v1.1",         ... },
  "consent_ledger":               [ ... ],
  "chain_of_custody":             [ ... ],
  "attestations":                 [ ... ],
  "redaction_manifest":           [ ... ],
  "evidence_quality":             { ... },
  "data_residency":               { ... },
  "training_permissions":         { ... },
  "model_risk":                   { ... },
  "retention_status":             { ... },
  "agent_observability":          { "schema_version": "gallodoc.agent_observability.v1.4",          ... },
  "trust_decision":               { "schema_version": "gallodoc.trust_decision.v1.5",               ... },
  "agent_supply_chain_security":  { "schema_version": "gallodoc.agent_supply_chain_security.v1.6",  ... },

  "query_access":                 { "schema_version": "gallodoc.query_access.v2.0",                 ... },
  "vector_context":               { "schema_version": "gallodoc.vector_context.v2.0",               ... },
  "document_relationships":       { "schema_version": "gallodoc.document_relationships.v2.0",       ... },
  "temporal_versions":            { "schema_version": "gallodoc.temporal_versions.v2.0",            ... },
  "policy_governance":            { "schema_version": "gallodoc.policy_governance.v2.0",            ... },
  "access_control":               { "schema_version": "gallodoc.access_control.v2.0",               ... },
  "human_review":                 { "schema_version": "gallodoc.human_review.v2.0",                 ... },
  "workflow_execution":           { "schema_version": "gallodoc.workflow_execution.v2.0",           ... },
  "connector_lineage":            { "schema_version": "gallodoc.connector_lineage.v2.0",            ... },
  "compute_trace":                { "schema_version": "gallodoc.compute_trace.v2.0",                ... },
  "artifact_bom":                 { "schema_version": "gallodoc.artifact_bom.v2.0",                 ... }
}
```

---

## 1. `query_access` — GalloDoc Query Language (GQL)

**Schema slug:** `gallodoc.query_access.v2.0`

Records the *intent* of a query, its *safe filter structure*, and a
*receipt* per execution. Public projection never carries raw dialect-specific
queries; the engine that resolves the query stays inside the implementation.

```json
{
  "schema_version": "gallodoc.query_access.v2.0",
  "saved_queries": [],
  "query_receipts": [],
  "query_permissions": []
}
```

**Saved query** — `query_id`, `name`, `purpose`, `query_type`
(`document` / `artifact` / `relationship` / `embedding` / `trust` / `policy` / `timeline`),
`filters` (structured JSON), `return_fields[]`, `max_results`, `safe_mode`,
`created_by_role`, `created_at`.

**Query receipt** — `receipt_id`, `query_id`, `executed_by_role`,
`executed_at`, `result_count`, `redaction_applied`, `phi_removed`,
`policy_outcome_ref`, `result_hash`.

**Query permission** — `permission_id`, `query_id`, `allowed_roles[]`,
`denied_roles[]`, `scope_summary`, `expires_at`.

**Privacy invariants.** No native-dialect query strings in public projection.
No PHI in query receipts. Filters and return-field allow-lists are stored
structurally so engines can replay the safe query without re-deriving intent.

---

## 2. `vector_context` — Native RAG

**Schema slug:** `gallodoc.vector_context.v2.0`

```json
{
  "schema_version": "gallodoc.vector_context.v2.0",
  "embedding_indexes": [],
  "embedding_chunks": [],
  "retrieval_receipts": []
}
```

**Embedding index** — `index_id`, `embedding_model_hash_or_id`, `dimensions`,
`distance_metric`, `chunking_strategy`, `created_at`.

**Embedding chunk** — `chunk_id`, `source_artifact_ref`, `source_span`,
`text_hash`, `token_count`, `embedding_hash`, `model_hash_or_id`,
`metadata_summary`, `created_at`.

**Retrieval receipt** — `retrieval_id`, `query_hash`, `index_id`, `top_k`,
`returned_count`, `selected_chunk_refs[]`, `score_summary`, `noise_flag`,
`policy_outcome_ref`, `created_at`.

**Privacy invariants.** Public envelope stores the embedding hash, not the
raw vector. Raw chunk text is optional and must be redacted/safe.
Retrieval traces from v1.4 (`agent_observability.retrieval_traces`) map
into `retrieval_receipts` so RAG behavior is provable from hashes and
chunk references alone.

---

## 3. `document_relationships`

**Schema slug:** `gallodoc.document_relationships.v2.0`

```json
{
  "schema_version": "gallodoc.document_relationships.v2.0",
  "relationships": [],
  "relationship_evidence": [],
  "relationship_decisions": []
}
```

**Relationship** — `relationship_id`, `source_document_ref`,
`target_document_ref`, `relationship_type`, `confidence` (0–1), `status`
(`suggested` / `confirmed` / `rejected`), `discovered_by`, `created_at`.

`relationship_type` enum:
`duplicate_of` | `version_of` | `supersedes` | `belongs_to` | `supports` |
`contradicts` | `same_claim` | `same_patient` | `same_customer` |
`same_contract` | `same_invoice` | `derived_from` | `related_to`.

**Relationship evidence** — `evidence_id`, `relationship_id`,
`evidence_type` (`shared_identifier` / `semantic_similarity` /
`exact_hash` / `human_review` / `external_reference`), `field_name`,
`value_hash`, `explanation_summary`.

**Relationship decision** — `decision_id`, `relationship_id`, `decision`,
`decided_by_role`, `decided_at`, `reason_code`.

**Privacy invariants.** PHI values that drove a match are represented by
`value_hash`, never the raw value.

---

## 4. `temporal_versions`

**Schema slug:** `gallodoc.temporal_versions.v2.0`

```json
{
  "schema_version": "gallodoc.temporal_versions.v2.0",
  "versions": [],
  "change_events": [],
  "replay_receipts": []
}
```

**Version** — `version_id`, `parent_version_id`, `document_hash`,
`gallodoc_hash`, `created_at`, `created_by_role`, `reason_code`,
`status` (`draft` / `active` / `superseded` / `archived`).

**Change event** — `change_id`, `from_version`, `to_version`, `change_type`
(`artifact_added` / `artifact_updated` / `decision_changed` /
`policy_changed` / `redaction_changed` / `relationship_changed` /
`trust_score_changed`), `field_path_hash`, `before_hash`, `after_hash`,
`summary`, `changed_at`.

**Replay receipt** — `replay_id`, `version_id`, `replayed_at`,
`replayed_by_role`, `output_hash`, `policy_version`, `success`.

**Privacy invariants.** "What changed" is recorded via `field_path_hash`,
`before_hash`, `after_hash` — never the raw before/after PHI.

---

## 5. `policy_governance`

**Schema slug:** `gallodoc.policy_governance.v2.0`

GalloDoc 2.0 records *policy decisions and the policy artifacts that
produced them* in a portable, engine-neutral way. Implementations are
free to use [Open Policy Agent (OPA)](https://www.openpolicyagent.org/)
and Rego, CEL, or a custom JSON rule engine — the open-core envelope
records hashes, names, condition summaries, and outcomes.

```json
{
  "schema_version": "gallodoc.policy_governance.v2.0",
  "policy_sets": [],
  "policy_rules": [],
  "policy_evaluations": []
}
```

**Policy set** — `policy_set_id`, `name`, `version`, `language`
(`json_rules` / `rego` / `cel` / `custom`), `policy_hash`, `status`
(`active` / `deprecated`).

**Policy rule** — `rule_id`, `policy_set_id`, `rule_name`, `purpose`,
`action` (`allow` / `warn` / `block` / `require_review`),
`condition_summary`, `severity`, `rule_hash`.

**Policy evaluation** — `evaluation_id`, `policy_set_id`, `subject_ref`,
`action`, `decision`, `matched_rule_refs[]`, `blockers[]`, `warnings[]`,
`evaluated_at`.

**Privacy invariants.** Raw enterprise policy formulas are never required
to ship publicly. `policy_hash` proves provenance; `condition_summary`
describes intent. v1.5 `decision_gates` may reference `evaluation_id` as
their authoritative policy outcome.

---

## 6. `access_control`

**Schema slug:** `gallodoc.access_control.v2.0`

```json
{
  "schema_version": "gallodoc.access_control.v2.0",
  "roles": [],
  "permissions": [],
  "masking_rules": [],
  "access_receipts": []
}
```

**Role** — `role_id`, `role_name`, `scope`.

**Permission** — `permission_id`, `role_id`, `action`, `subject_type`,
`allowed`, `constraints[]`.

**Masking rule** — `masking_rule_id`, `field_class`, `policy`,
`display_mode` (`hidden` / `masked` / `hashed` / `role_based`),
`applies_to_roles[]`.

**Access receipt** — `receipt_id`, `actor_role`, `action`, `subject_ref`,
`decision` (`allow` / `deny` / `masked`), `policy_evaluation_ref`,
`accessed_at`.

**Privacy invariants.** Never store user identity in open-core examples.
Use `actor_role` only (or a hashed actor handle on the enterprise side).
Access receipts prove who/what/when/why without leaking identity or PHI.

---

## 7. `human_review`

**Schema slug:** `gallodoc.human_review.v2.0`

```json
{
  "schema_version": "gallodoc.human_review.v2.0",
  "review_queues": [],
  "review_actions": [],
  "review_outcomes": []
}
```

**Review queue** — `queue_id`, `queue_name`, `priority`, `owner_role`,
`open_count`, `closed_count`.

**Review action** — `review_id`, `subject_ref`, `reviewer_role`,
`him_c_certified`, `action` (`approve` / `reject` / `correct` /
`escalate` / `request_more_evidence`), `reason_code`, `notes_hash`,
`decided_at`, `evidence_refs[]`.

**Review outcome** — `outcome_id`, `subject_ref`, `outcome`,
`override_flag`, `trust_score_delta`, `policy_evaluation_ref`,
`created_at`.

**Privacy invariants.** Reviewer notes are not stored by default — only
`notes_hash` and an optional safe `notes_summary`. Reviewer identity is
recorded by role only.

---

## 8. `workflow_execution`

**Schema slug:** `gallodoc.workflow_execution.v2.0`

A projection of GalloDoc lifecycle / app runs / pipeline runs into a
single representation. The v1.0 `lifecycle` block remains the
authoritative lifecycle history; this block expresses the same activity
as a structured workflow with input/output hashes per step.

```json
{
  "schema_version": "gallodoc.workflow_execution.v2.0",
  "workflow_runs": [],
  "workflow_steps": [],
  "workflow_artifacts": []
}
```

**Workflow run** — `workflow_run_id`, `workflow_name`, `app_slug`,
`status` (`queued` / `running` / `completed` / `failed` / `blocked`),
`started_at`, `completed_at`, `actor_role`, `purpose`.

**Workflow step** — `step_id`, `workflow_run_id`, `step_name`,
`step_type` (`ingest` / `ocr` / `classify` / `extract` / `review` /
`verify` / `export` / `scan` / `notify`), `status`, `input_hash`,
`output_hash`, `duration_ms`, `error_summary`.

**Workflow artifact** — `artifact_id`, `workflow_run_id`, `artifact_ref`,
`artifact_family`, `created_at`.

**Privacy invariants.** Step inputs and outputs are stored as hashes;
`error_summary` is a sanitized human-readable string, never a stack
trace with payload data.

---

## 9. `connector_lineage`

**Schema slug:** `gallodoc.connector_lineage.v2.0`

```json
{
  "schema_version": "gallodoc.connector_lineage.v2.0",
  "connector_sources": [],
  "sync_runs": [],
  "record_receipts": []
}
```

**Connector source** — `connector_slug`, `connector_category`,
`auth_type`, `status`, `source_system_hash_or_id`.

**Sync run** — `sync_run_id`, `connector_slug`, `started_at`,
`completed_at`, `status`, `records_seen`, `records_ingested`, `failures`.

**Record receipt** — `receipt_id`, `sync_run_id`, `record_hash`,
`source_object_type`, `source_record_id_hash`, `gallodoc_ref`,
`policy_evaluation_ref`, `created_at`.

**Privacy invariants.** Source identifiers are referenced by hash. No
credentials, no raw URLs, no customer record values. The block extends
(does not replace) the v1.0 `source` section.

---

## 10. `compute_trace`

**Schema slug:** `gallodoc.compute_trace.v2.0`

A unified, vendor-neutral trace model for AI calls, tool calls,
retrieval, policy evaluations, scanners, sandboxes, exports, and API
calls. Designed to be compatible with the
[OpenTelemetry](https://opentelemetry.io/) trace / metrics / logs
semantic model so traces can be exported to standard backends without
GalloDoc consumers depending on any specific vendor.

```json
{
  "schema_version": "gallodoc.compute_trace.v2.0",
  "spans": [],
  "metrics": [],
  "logs": []
}
```

**Span** — `span_id`, `parent_span_id`, `trace_id`, `span_name`,
`span_type` (`llm_call` / `tool_call` / `retrieval` / `policy_eval` /
`scanner` / `sandbox` / `export` / `api_call`), `started_at`,
`ended_at`, `duration_ms`, `status`, `input_hash`, `output_hash`,
`error_summary`, `linked_receipt_refs[]`.

**Metric** — `metric_id`, `trace_id`, `name`, `value`, `unit`,
`tags_summary`, `recorded_at`.

**Log** — `log_id`, `trace_id`, `level`, `event_name`, `message_summary`,
`timestamp`.

**Privacy invariants.** No raw logs with PHI or secrets. Logs and metrics
record summaries and hashes only. v1.4 `agent_observability` traces,
model verifications, skill scans, and workflow steps all project into
this block.

---

## 11. `artifact_bom`

**Schema slug:** `gallodoc.artifact_bom.v2.0`

A software / artifact bill-of-materials for any package GalloDoc
references. Compatible at the field-level with widely used SBOM formats
[SPDX](https://spdx.dev/) (license/compliance focus) and
[CycloneDX](https://cyclonedx.org/) (vulnerability/security focus); the
GalloDoc projection is intentionally a small superset of common fields
so external SBOMs can be imported losslessly.

```json
{
  "schema_version": "gallodoc.artifact_bom.v2.0",
  "components": [],
  "dependencies": [],
  "vulnerabilities": [],
  "licenses": []
}
```

**Component** — `component_id`, `name`, `version`, `component_type`
(`document` / `model` / `skill` / `mcp_tool` / `python_package` /
`npm_package` / `container` / `dataset`), `hash`, `supplier_hash_or_id`,
`purl`, `bom_ref`.

**Dependency** — `dependency_id`, `from_component`, `to_component`,
`relationship`.

**Vulnerability** — `vulnerability_id`, `component_ref`, `severity`,
`source`, `advisory_ref`, `status`.

**License** — `license_id`, `component_ref`, `license_name`,
`license_hash_or_id`.

**Privacy invariants.** Public examples use synthetic package names and
hashes. No malware payloads, no live advisory bodies. Real advisory text
remains in the upstream advisory source; this block stores only the
reference.

---

## Forbidden subtree categories (still enforced)

The validator and `scripts/release_safety_scan.py` continue to forbid the
following named keys anywhere inside any v1.x or v2.0 block. Listing them
here is the contract — they MUST NOT appear in public examples or
production envelopes:

- raw transcript / model-call subtrees
- raw model thinking traces
- raw retrieval chunk bodies
- raw PHI subtrees
- model weight / fine-tune dataset / adapter / gradient subtrees
- credential / signing material / bearer-token subtrees
- session / IP correlation hashes used at the open-core surface
- tenant boundary identifiers (boundary names are public; raw boundary
  IDs stay enterprise-side)

The full enforced key list lives in [`../privacy-and-safety.md`](../privacy-and-safety.md)
and the validator [`../../gallodoc/validation/__init__.py`](../../gallodoc/validation/__init__.py).

## Reference

- [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
  — single envelope demonstrating every v2.0 block side-by-side with the
  v1.0–v1.6 sections.
- [`../../RELEASE_NOTES_2.0.0.md`](../../RELEASE_NOTES_2.0.0.md) — release
  candidate notes and migration story.
- Per-block specs:
  [`gallodoc-query-language-v2.md`](gallodoc-query-language-v2.md),
  [`gallodoc-vector-context-v2.md`](gallodoc-vector-context-v2.md),
  [`gallodoc-document-relationships-v2.md`](gallodoc-document-relationships-v2.md),
  [`gallodoc-temporal-versions-v2.md`](gallodoc-temporal-versions-v2.md),
  [`gallodoc-policy-governance-v2.md`](gallodoc-policy-governance-v2.md),
  [`gallodoc-access-control-v2.md`](gallodoc-access-control-v2.md),
  [`gallodoc-human-review-v2.md`](gallodoc-human-review-v2.md),
  [`gallodoc-workflow-execution-v2.md`](gallodoc-workflow-execution-v2.md),
  [`gallodoc-connector-lineage-v2.md`](gallodoc-connector-lineage-v2.md),
  [`gallodoc-compute-trace-v2.md`](gallodoc-compute-trace-v2.md),
  [`gallodoc-artifact-bom-v2.md`](gallodoc-artifact-bom-v2.md).
