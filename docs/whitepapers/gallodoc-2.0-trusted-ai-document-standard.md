---
title: "GalloDoc 2.0: A Standard for Trusted AI Documents, Data, and Agents"
version: "2.0.0"
status: release-candidate
audience: "enterprise leaders; platform teams; AI governance teams; security reviewers; compliance owners"
last_updated: "2026-05-02"
keywords: "GalloDoc 2.0, trusted AI, document intelligence, AI governance, RAG, query language, policy, access control, human review, workflow, connector lineage, compute trace, SBOM"
---

# GalloDoc 2.0: A Standard for Trusted AI Documents, Data, and Agents

## 1. Executive Summary

GalloDoc 2.0 is the consolidated open standard for trusted AI documents,
data, and agents. It collects the v1.0 traceable document envelope and the
v1.1–v1.6 amendments, then standardizes the platform primitives that every
team kept rebuilding: a safe query language, native RAG, cross-document
relationships, temporal versioning, a portable policy/rule layer, access
control with masking, human review, workflow execution, connector lineage,
a unified compute trace, and a software bill-of-materials.

GalloDoc 2.0 is **additive** and **backward-compatible**: every v1.x
envelope is still a valid GalloDoc 2.0 envelope, and every v2.0 block is
optional. Implementations adopt blocks where they have data and skip the
rest. This is not a new schema; it is the consolidated standard.

## 2. Why Documents Alone Are Not Enough

Operational systems run on documents — contracts, claims, notes, exports,
emails, scans — but raw documents do not know what they prove or to whom.
Storage, retrieval, and OCR alone cannot answer audit questions or feed AI
safely. Without a structured, traceable envelope every workflow rebuilds
the same plumbing.

## 3. Why AI Outputs Alone Are Not Enough

AI outputs without provenance, evidence, or governance fail the same audit
questions a stack of PDFs fails: who produced this, on what evidence, under
what permission, and against which policy version. AI fluency is not
trust. Trust is structural.

## 4. The Missing Trust Layer

The trust layer is the part that makes a document/AI artifact decision-ready:

- *traceable* (v1.0)
- *governed* (v1.1)
- *consented* (v1.2)
- *risk-aware* (v1.3)
- *observable* (v1.4)
- *trust-scored* (v1.5)
- *supply-chain-safe* (v1.6)
- *queryable, retrievable, related, versioned, policy-governed,
  access-controlled, human-reviewable, workflow-bound, lineage-traced,
  compute-accounted, BOM-described* (2.0)

## 5. What 1.0–1.6 Established

- **v1.0** — the traceable envelope: identity, source, purpose, lifecycle,
  activity, evidence, validations, security, exports, AI usage,
  GalloUnits, certification, GSTP, truth ledger.
- **v1.1** — execution governance: capability tokens, contracts, requests
  and receipts (hashes only).
- **v1.2** — consent ledger, chain of custody, human decisions,
  attestations, redaction manifest, evidence quality.
- **v1.3** — residency, training permissions, model risk, retention
  status.
- **v1.4** — agent observability: traces, tool logs, retrieval traces,
  reasoning summaries, evaluations, latency/cost, failure analyses,
  regression tests, escalation decisions.
- **v1.5** — trust scores, decision gates, policy outcomes, action
  recommendations, decision receipts.
- **v1.6** — agent supply chain security: scans, findings, manifests,
  permission reviews, dependency reviews, sandbox observations, LLM
  security reviews, quarantine decisions, install receipts.

## 6. What 2.0 Standardizes

GalloDoc 2.0 makes ten platform primitives portable. Every block is
optional and stores hashes, summaries, role names, status enums, score
ranges, and timestamps — never raw payloads, raw secrets, or raw PHI.

## 7. Query, Relationships, and Vector Context

- **`query_access`** — the GalloDoc Query Language (GQL): structured JSON
  queries with filters, return-field allow-lists, and a per-execution
  receipt. Public projection never carries native dialect-specific
  queries.
- **`document_relationships`** — first-class cross-document edges with
  evidence and explicit confirm/reject decisions. PHI values that drove a
  match are stored as `value_hash`.
- **`vector_context`** — native RAG: embedding indexes, chunk hashes,
  retrieval receipts. Vectors stay in the engine; the envelope stores
  hashes and references so retrieval is provable without exposing
  embeddings or chunk bodies.

## 8. Policy, Access, and Human Review

- **`policy_governance`** — engine-neutral policy/rule layer
  (OPA/Rego-compatible by convention). The envelope records `policy_hash`,
  `condition_summary`, action, severity, and evaluation outcome — not the
  rule body.
- **`access_control`** — roles, permissions, masking rules, and access
  receipts. Open-core never carries user identity; only `actor_role`.
- **`human_review`** — HIM-C-style review queues, actions, and outcomes.
  Reviewer notes are hashed by default; a sanitized summary is optional.

## 9. Workflow, Connector Lineage, and Compute Trace

- **`workflow_execution`** — pipelines, steps, and step-level artifacts as
  a projection of the v1.0 lifecycle. Step inputs/outputs are hashes.
- **`connector_lineage`** — connector sources, sync runs, and per-record
  receipts. Source identifiers and external record IDs are hashed.
- **`compute_trace`** — a vendor-neutral spans/metrics/logs model designed
  to be compatible with the [OpenTelemetry](https://opentelemetry.io/)
  semantic conventions for traces, metrics, and logs. `agent_observability`
  remains the AI-specific lens; `compute_trace` unifies the cross-cutting
  view across AI, tools, scanners, and workflows.

## 10. Agent Supply Chain Security

GalloDoc 2.0 keeps **`agent_supply_chain_security`** unchanged from v1.6.
The 2.0 BOM block (`artifact_bom`) complements it with a software/artifact
bill-of-materials whose field shapes overlap with [SPDX](https://spdx.dev/)
and [CycloneDX](https://cyclonedx.org/) so external SBOMs can be imported
losslessly. Public examples carry synthetic component names and hashes;
no live advisories or malware payloads ship in the package.

## 11. Enterprise Use Cases

- **Audit-ready RAG.** `vector_context.retrieval_receipts` plus v1.4
  retrieval traces let auditors see what was retrieved without seeing
  what was inside.
- **Document-scale compliance review.** `query_access` records intent and
  receipts; `policy_governance` records the rule that decided; v1.5
  `decision_gates` link the receipt.
- **Cross-document case packets.** `document_relationships` makes
  duplicates, claim pairs, and patient/customer joins explicit and
  reviewable.
- **Safe agent platforms.** v1.6 supply chain security plus v2.0
  `artifact_bom` give buyers a defensible answer to "what is in this
  agent?" without shipping the agent code itself.
- **Time-aware governance.** `temporal_versions` records what changed,
  when, and under which policy version, with replay receipts proving a
  past version still produces the same hashed output.

## 12. Open-Core vs Enterprise

The open-core package keeps the schema, validator, examples, CLI, and
release safety scan. Enterprise deployments attach the proprietary parts:
the actual policy bodies, the live vector store, the production query
engine, the customer connectors, the certification keys, and the trust
score weights. The boundary is intentionally narrow: the *standard* is
public; the *implementation* is yours.

## 13. Conclusion

GalloDoc 2.0 turns the question "is this document/AI artifact trustworthy?"
into a structural answer. The envelope says what it knows, what it
proves, who touched it, what changed, what it cost, and how it can be
queried — all without leaking the things a public envelope must never
leak. v2.0 is a release candidate. PyPI publication is manual; this paper
does not imply a final 2.0.0 release until maintainers ship it.
