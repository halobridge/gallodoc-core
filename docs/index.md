# GalloDoc Core — documentation

Welcome. This is the documentation index for the open-source `gallodoc`
package. The repository's [`README.md`](../README.md) is the marketing /
quickstart entry point; the pages here are the technical reference.

## Spec

| Page | What it covers |
|---|---|
| [`gallodoc-core-v1.md`](gallodoc-core-v1.md) | The frozen v1 envelope schema — required vs optional sections, enum values, types, the projection contract. |
| [`gallodoc-units-v1.md`](gallodoc-units-v1.md) | GalloUnits v1 — model-agnostic semantic evidence units, source spans, text hashes, model projections. |
| [`gstp-v1.md`](gstp-v1.md) | GalloDoc Secure Transport Package — manifest shape, canonical JSON hashing, verification procedure, revocation model. |
| [`GALLODOC_CORE_V1_FROZEN.md`](GALLODOC_CORE_V1_FROZEN.md) | Formal freeze declaration and stability rules. |

### Amendments (same schema family `gallodoc-core/v1`)

Optional top-level blocks build on the frozen v1.0 envelope without breaking older payloads.

| Amendment | Spec | What it adds |
|-----------|------|----------------|
| **v1.1** — Execution governance | [`specs/gallodoc-core-v1.1-execution-governance.md`](specs/gallodoc-core-v1.1-execution-governance.md) | `execution_governance` — capability tokens, contracts, execution requests/receipts (hashes and opaque IDs only). |
| **v1.2** — Consent, custody, attestation | [`specs/gallodoc-core-v1.2-consent-custody-attestation.md`](specs/gallodoc-core-v1.2-consent-custody-attestation.md) | `consent_ledger`, `chain_of_custody`, `human_decisions`, `attestations`, `redaction_manifest`, `evidence_quality` — compliance metadata only. |
| **v1.3** — Residency, training, model risk | [`specs/gallodoc-core-v1.3-residency-training-model-risk.md`](specs/gallodoc-core-v1.3-residency-training-model-risk.md) | `data_residency`, `training_permissions`, `model_risk`, `retention_status` — AI risk / data-governance summaries (no raw prompts, weights, or training payloads). |
| **v1.4** — Agent observability | [`specs/gallodoc-core-v1.4-agent-observability.md`](specs/gallodoc-core-v1.4-agent-observability.md) | `agent_observability` — traces, tool logs, retrieval summaries, evaluations, failures, regressions, and escalations. |
| **v1.5** — Trust decision | [`specs/gallodoc-core-v1.5-trust-decision.md`](specs/gallodoc-core-v1.5-trust-decision.md) | `trust_decision` — trust scores, decision gates, policy outcomes, recommendations, and receipts. |
| **v1.6** — Agent supply chain security | [`specs/gallodoc-core-v1.6-agent-supply-chain-security.md`](specs/gallodoc-core-v1.6-agent-supply-chain-security.md) | `agent_supply_chain_security` — install/run/delegation risk for skills, MCP tools, prompt packs, browser agents, and executable skill bundles. |
| **2.0 (consolidated)** | [`specs/gallodoc-core-v2.0-master-spec.md`](specs/gallodoc-core-v2.0-master-spec.md) | Adds optional, additive top-level blocks: `query_access`, `vector_context`, `document_relationships`, `temporal_versions`, `policy_governance`, `access_control`, `human_review`, `workflow_execution`, `connector_lineage`, `compute_trace`, `artifact_bom`. |

## How-to

| Page | What it covers |
|---|---|
| [`ai-usage-ledger.md`](ai-usage-ledger.md) | How to record AI calls against a GalloDoc, what the helpers do, what the privacy invariants are. |
| [`artifacts.md`](artifacts.md) | The basic regex-based artifact extractor — types, fields, confidence model. |
| [`examples.md`](examples.md) | Tour of every synthetic envelope under `examples/` and what each one demonstrates. |

## White Papers

| Paper | What it covers |
|---|---|
| [`whitepapers/gallodoc-1.0-from-documents-to-structured-intelligence.md`](whitepapers/gallodoc-1.0-from-documents-to-structured-intelligence.md) | GalloDoc 1.0 — From Documents to Structured Intelligence. |
| [`whitepapers/gallodoc-1.1-governing-ai-execution.md`](whitepapers/gallodoc-1.1-governing-ai-execution.md) | GalloDoc 1.1 — Governing AI Execution. |
| [`whitepapers/gallodoc-1.2-consent-custody-attestation.md`](whitepapers/gallodoc-1.2-consent-custody-attestation.md) | GalloDoc 1.2 — Consent, Custody, and Attestation. |
| [`whitepapers/gallodoc-1.3-ai-data-governance-risk-control.md`](whitepapers/gallodoc-1.3-ai-data-governance-risk-control.md) | GalloDoc 1.3 — AI Data Governance and Risk Control. |
| [`whitepapers/gallodoc-1.4-observable-ai.md`](whitepapers/gallodoc-1.4-observable-ai.md) | GalloDoc 1.4 — Observable AI. |
| [`whitepapers/gallodoc-1.5-measuring-trust-in-ai-decisions.md`](whitepapers/gallodoc-1.5-measuring-trust-in-ai-decisions.md) | GalloDoc 1.5 — Measuring Trust in AI Decisions. |
| [`whitepapers/gallodoc-2.0-trusted-ai-document-standard.md`](whitepapers/gallodoc-2.0-trusted-ai-document-standard.md) | GalloDoc 2.0 — A Standard for Trusted AI Documents, Data, and Agents. |
| [`whitepapers/index.md`](whitepapers/index.md) | White paper set landing page. |

## Boundaries

| Page | What it covers |
|---|---|
| [`open-core-vs-enterprise.md`](open-core-vs-enterprise.md) | What ships in the open-source package vs what stays in HaloBridge enterprise. |
| [`privacy-and-safety.md`](privacy-and-safety.md) | The privacy invariants enforced by the projection function and the release safety scanner. |

## CLI

```
gallodoc validate   <file> [<file> ...]   # one or more envelopes (core + v1.1–v1.3 examples)
gallodoc inspect    <file>              # human-friendly summary
gallodoc units      <text-file>         # segment text into GalloUnits
gallodoc extract    <text-file>         # regex-based artifact extraction
gallodoc gstp verify <package>          # verify a GSTP package or manifest
```

`gallodoc validate` accepts multiple paths (and shell globs such as
`examples/v1_1/*.json`). With `--json`, a single file prints one result
object; multiple files print a JSON array of `{ "file": ..., ... }` objects.

All subcommands accept `--json` for machine-readable output and exit `0` on
success / `1` on failure.

## Project status

GalloDoc Core **2.0 release candidate** — Python package **2.0.0** (PyPI
release is manual; prefer a source checkout for the latest RC). The schema
identifier on the wire remains **`gallodoc-core/v1`** (frozen base);
v1.1–v1.6 amendments and the v2.0 platform blocks are documented in
[`specs/`](specs/). See
[`../RELEASE_NOTES_2.0.0.md`](../RELEASE_NOTES_2.0.0.md),
[`../RELEASE_NOTES_1.5.0.md`](../RELEASE_NOTES_1.5.0.md),
[`../RELEASE_NOTES_1.3.0.md`](../RELEASE_NOTES_1.3.0.md),
[`../RELEASE_NOTES_0.1.0.md`](../RELEASE_NOTES_0.1.0.md), and
[`../CHANGELOG.md`](../CHANGELOG.md).
