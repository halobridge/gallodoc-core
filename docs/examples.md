# Examples — guided tour

Every example under [`../examples/`](../examples/) validates against
`gallodoc-core/v1`, contains no real PHI / PII, and demonstrates a
specific section of the schema. All identifiers are synthetic.

## Quick validate-them-all

Core examples plus amendment bundles (v1.1, v1.2, v1.3):

```bash
for f in examples/gallodoc_*.json examples/v1_1/*.json examples/v1_2/*.json examples/v1_3/*.json examples/v1_4/*.json; do
  [ -e "$f" ] || continue
  gallodoc validate "$f"
done
```

Or pass globs directly (multi-file validate):

```bash
gallodoc validate examples/v1_1/*.json
gallodoc validate examples/v1_2/*.json
gallodoc validate examples/v1_3/*.json
gallodoc validate examples/v1_4/*.json
```

## Files

| File | Demonstrates |
|---|---|
| `gallodoc_pdf_contract.json` | Document upload, lifecycle stages, app-execution metadata, classification + extraction unit projections (clauses + per-model token counts), AI usage ledger entry. |
| `gallodoc_sql_claim_row.json` | Connector-sourced row with PHI categories, encrypted fields, masked fields, model verification disagreement, two-AI-run ledger, claim/service-line GalloUnits. |
| `gallodoc_fhir_patient_record.json` | FHIR-bundle source with high PHI risk level, encryption posture, redaction policy. |
| `gallodoc_image_insurance_card.json` | OCR'd image with bounded `media.regions[]` and PHI-redaction posture. |
| `gallodoc_audio_call_recording.json` | Audio segment GalloUnit with `start_time_ms` / `end_time_ms` and a redacted transcript summary. |
| `gallodoc_video_procedure_clip.json` | Video segment GalloUnit with both temporal + spatial source span. |
| `gallodoc_website_compliance_scan.json` | Crawled marketing-site evidence, contradiction signals, FDA `external_evidence` reference. |
| `gallodoc_connector_salesforce_record.json` | Salesforce-style CRM record with `connector_source` block and `derived_from` relationship edge. |
| `gallodoc_external_evidence_packet.json` | Audit-evidence packet with FDA / CMS / public-authority external references. |
| `gallodoc_certified_export_gstp_reference.json` | Fully certified envelope with Providence Certifier, GSTP package metadata, and a populated Truth Ledger snapshot. |

### GalloDoc Core v1.1 — execution governance

Optional additive envelopes live under [`examples/v1_1/`](../examples/v1_1/). They include a top-level `execution_governance` block (`schema_version`: `gallodoc.execution_governance.v1.1`) with capability tokens, contracts, requests, and **receipts** (hashes and opaque IDs only — no prompt bodies or OAuth material).

| File | Demonstrates |
|---|---|
| `gallodoc_v1_1_execution_governance_reference.json` | Full v1.1 execution governance shape with safe receipts and contracts. |

```bash
gallodoc validate examples/v1_1/gallodoc_v1_1_execution_governance_reference.json
```

Spec: [`specs/gallodoc-core-v1.1-execution-governance.md`](specs/gallodoc-core-v1.1-execution-governance.md).

### GalloDoc Core v1.2 — consent, custody, attestation

Under [`examples/v1_2/`](../examples/v1_2/): optional compliance blocks (`consent_ledger`, `chain_of_custody`, `human_decisions`, `attestations`, `redaction_manifest`, `evidence_quality`) — metadata and hashes only.

| File | Demonstrates |
|---|---|
| `gallodoc_consent_custody_attestation.json` | Synthetic consent entries, custody events, human decisions, attestations, redaction manifest, evidence quality summary. |

```bash
gallodoc validate examples/v1_2/gallodoc_consent_custody_attestation.json
```

Spec: [`specs/gallodoc-core-v1.2-consent-custody-attestation.md`](specs/gallodoc-core-v1.2-consent-custody-attestation.md).

### GalloDoc Core v1.3 — residency, training permission, model risk

Under [`examples/v1_3/`](../examples/v1_3/): optional AI risk / data-governance blocks (`data_residency`, `training_permissions`, `model_risk`, `retention_status`) — regions, enums, hashed model ids; **no** raw prompts, responses, or weight payloads.

| File | Demonstrates |
|---|---|
| `gallodoc_residency_training_model_risk.json` | Residency boundaries, training permission summary, external model risk posture, retention snapshot. |

```bash
gallodoc validate examples/v1_3/gallodoc_residency_training_model_risk.json
```

Spec: [`specs/gallodoc-core-v1.3-residency-training-model-risk.md`](specs/gallodoc-core-v1.3-residency-training-model-risk.md).

### GalloDoc Core v1.4 — agent observability

Under [`examples/v1_4/`](../examples/v1_4/): optional agent observability (`agent_observability`) — traces, tool logs, retrieval summaries, metrics, evaluations, failures, regressions, escalations; **no** raw prompts, responses, or PHI chunks.

```bash
gallodoc validate examples/v1_4/gallodoc_agent_observability.json
gallodoc inspect examples/v1_4/gallodoc_agent_observability.json
```

Spec: [`specs/gallodoc-core-v1.4-agent-observability.md`](specs/gallodoc-core-v1.4-agent-observability.md).

### GalloDoc Core v1.5 — trust decision

Under [`examples/v1_5/`](../examples/v1_5/): optional trust decision (`trust_decision`) — trust scores with explainable components, decision gates, policy outcomes, recommendations, and receipts; **no** proprietary weight formulas or sensitive payloads.

```bash
gallodoc validate examples/v1_5/gallodoc_trust_decision.json
gallodoc inspect examples/v1_5/gallodoc_trust_decision.json
```

Spec: [`specs/gallodoc-core-v1.5-trust-decision.md`](specs/gallodoc-core-v1.5-trust-decision.md).

### GalloDoc Core v1.6 — agent supply chain security

Under [`examples/v1_6/`](../examples/v1_6/): optional agent supply chain security (`agent_supply_chain_security`) — scans, findings, package manifests, permission reviews, dependency reviews, sandbox observations, LLM security reviews, quarantine decisions, and install receipts; **no** raw secrets, PHI, executable payloads, or host execution output.

```bash
gallodoc validate examples/v1_6/gallodoc_agent_supply_chain_security.json
gallodoc inspect examples/v1_6/gallodoc_agent_supply_chain_security.json
```

Spec: [`specs/gallodoc-core-v1.6-agent-supply-chain-security.md`](specs/gallodoc-core-v1.6-agent-supply-chain-security.md).

### GalloDoc Core 2.0 — consolidated reference + per-block demos

Under [`examples/v2_0/`](../examples/v2_0/): one consolidated reference plus
one minimal demo per v2.0 optional top-level block. Each block-specific
example is a v1.5 base envelope with **only** that v2.0 block populated, so
each one is the smallest valid demo of a single block.

| File | Demonstrates |
|---|---|
| `gallodoc_full_v2_reference.json`         | All 11 v2.0 blocks side-by-side with the v1.0 envelope and the v1.1–v1.6 amendments. |
| `gallodoc_query_access.json`              | `query_access` — saved queries, query receipts, query permissions ([spec](specs/gallodoc-query-language-v2.md)). |
| `gallodoc_vector_context.json`            | `vector_context` — embedding indexes, embedding chunks (hashes only), retrieval receipts ([spec](specs/gallodoc-vector-context-v2.md)). |
| `gallodoc_document_relationships.json`    | `document_relationships` — first-class cross-document edges, evidence, decisions ([spec](specs/gallodoc-document-relationships-v2.md)). |
| `gallodoc_temporal_versions.json`         | `temporal_versions` — versions, change events, replay receipts ([spec](specs/gallodoc-temporal-versions-v2.md)). |
| `gallodoc_policy_governance.json`         | `policy_governance` — policy sets, rules, evaluations (engine-neutral) ([spec](specs/gallodoc-policy-governance-v2.md)). |
| `gallodoc_access_control.json`            | `access_control` — roles, permissions, masking rules, access receipts ([spec](specs/gallodoc-access-control-v2.md)). |
| `gallodoc_human_review.json`              | `human_review` — review queues, actions, outcomes ([spec](specs/gallodoc-human-review-v2.md)). |
| `gallodoc_workflow_execution.json`        | `workflow_execution` — pipelines, steps, artifacts ([spec](specs/gallodoc-workflow-execution-v2.md)). |
| `gallodoc_connector_lineage.json`         | `connector_lineage` — connector sources, sync runs, record receipts ([spec](specs/gallodoc-connector-lineage-v2.md)). |
| `gallodoc_compute_trace.json`             | `compute_trace` — spans, metrics, logs (OpenTelemetry-compatible) ([spec](specs/gallodoc-compute-trace-v2.md)). |
| `gallodoc_artifact_bom.json`              | `artifact_bom` — components, dependencies, vulnerabilities, licenses (SPDX/CycloneDX-compatible) ([spec](specs/gallodoc-artifact-bom-v2.md)). |

```bash
gallodoc validate examples/v2_0/*.json
gallodoc inspect  examples/v2_0/gallodoc_full_v2_reference.json
```

Master spec: [`specs/gallodoc-core-v2.0-master-spec.md`](specs/gallodoc-core-v2.0-master-spec.md).
White paper: [`whitepapers/gallodoc-2.0-trusted-ai-document-standard.md`](whitepapers/gallodoc-2.0-trusted-ai-document-standard.md).

## Inspect any example

```bash
gallodoc inspect examples/gallodoc_pdf_contract.json --json
```

The inspector prints `schema_version`, document id, type, source, GalloUnit
count, AI usage totals, certification status, GSTP status, and Truth
Ledger state — all in one short summary suitable for piping into `jq`.

## Build your own

The smallest valid envelope is the schema's required sections with safe
empty values:

```python
from gallodoc import GALLODOC_CORE_VERSION

env = {
    "schema_version": GALLODOC_CORE_VERSION,
    "identity": {"gallodoc_id": "doc-001", "schema_version": GALLODOC_CORE_VERSION},
    "source": {},
    "purpose": {"primary_intent": "general_document_intelligence", "workflow_intent": "unspecified"},
    "lifecycle": {"available": False, "stages": [], "provenance_chain": []},
    "activity": {"available": False, "event_count": 0, "counts_by_type": {}, "latest_events": []},
    "relationships": [],
    "evidence": {"count": 0, "refs": []},
    "validations": {"contradictions": []},
    "security": {"phi_detected": False, "phi_risk_level": "none", "encrypted": False, "raw_export_allowed": True, "encryption_policy_status": "not_required"},
    "exports": [],
    "extensions": {},
    "ai_usage": {"summary": {"total_runs": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_tokens": 0, "estimated_total_cost": 0.0, "currency": "USD"}, "runs": []},
    "gallounits": {"unit_strategy": "gallounit_v1", "units": [], "model_projections": []},
    "certification": {"status": "none", "certification_type": "none"},
    "gstp": {"package_id": "", "package_type": "gallodoc_secure_transport_package", "status": "not_created"},
    "truth_ledger": {"available": False, "truth_state": "uncertified"},
}
```

`validate_envelope(env)` returns `valid: True` for the above. From there
add only what your workflow needs.
