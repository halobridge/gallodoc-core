# GalloDoc Core 2.0.0 — release notes (release candidate)

**Date:** 2026-05-02
**Status:** release candidate (**Development Status :: Alpha** in `pyproject.toml`)
**Schema family:** `gallodoc-core/v1` — **frozen base**; **v1.1–v1.6** are
optional additive amendments; **v2.0** introduces optional, additive
*platform* blocks. The on-the-wire envelope identifier is unchanged for
full backward compatibility.

This release candidate bumps the **Python package** to **2.0.0**. It does
**not** rename or change the envelope `schema_version`. PyPI publication is
manual; this document does not imply a package is live on the index until
maintainers publish.

---

## Highlights

GalloDoc 2.0 consolidates v1.0–v1.6 and adds the missing platform layer.
**Every v2.0 block is optional and additive.** Older consumers ignore
unknown keys.

### New optional top-level blocks

| Top-level key             | Slug                                       | Adds |
|---------------------------|--------------------------------------------|------|
| `query_access`            | `gallodoc.query_access.v2.0`               | GalloDoc Query Language (GQL) — saved queries, query receipts, query permissions. |
| `vector_context`          | `gallodoc.vector_context.v2.0`             | Native RAG — embedding indexes, embedding chunks, retrieval receipts. |
| `document_relationships`  | `gallodoc.document_relationships.v2.0`     | First-class cross-document edges, evidence, decisions. |
| `temporal_versions`       | `gallodoc.temporal_versions.v2.0`          | Versioning + replay — versions, change events, replay receipts. |
| `policy_governance`       | `gallodoc.policy_governance.v2.0`          | Portable policy/rule layer (OPA/Rego-compatible) — sets, rules, evaluations. |
| `access_control`          | `gallodoc.access_control.v2.0`             | Roles, permissions, masking rules, access receipts. |
| `human_review`            | `gallodoc.human_review.v2.0`               | HIM-C-style queues, actions, outcomes. |
| `workflow_execution`      | `gallodoc.workflow_execution.v2.0`         | Pipelines + steps + artifacts as a projection of lifecycle/app runs. |
| `connector_lineage`       | `gallodoc.connector_lineage.v2.0`          | Connector sources, sync runs, record receipts. |
| `compute_trace`           | `gallodoc.compute_trace.v2.0`              | Unified spans/metrics/logs (OpenTelemetry-compatible at the semantic layer). |
| `artifact_bom`            | `gallodoc.artifact_bom.v2.0`               | Software/artifact bill-of-materials (SPDX/CycloneDX-compatible fields). |

Reference: [`docs/specs/gallodoc-core-v2.0-master-spec.md`](docs/specs/gallodoc-core-v2.0-master-spec.md).
Example: [`examples/v2_0/gallodoc_full_v2_reference.json`](examples/v2_0/gallodoc_full_v2_reference.json).

White paper (narrative): [`docs/whitepapers/gallodoc-2.0-trusted-ai-document-standard.md`](docs/whitepapers/gallodoc-2.0-trusted-ai-document-standard.md).

---

## Compatibility

- **Schema family unchanged.** Top-level `schema_version` on every envelope
  still equals `gallodoc-core/v1`.
- **No removals.** All v1.0–v1.6 blocks keep the same field names and
  semantics.
- **All v1.0–v1.6 example envelopes still validate** against the bundled
  validator and against the JSON-Schema (when `[schema]` extras are
  installed).
- **All v2.0 blocks are optional**; an envelope that omits them is a valid
  v2.0 envelope.

## Open-core guarantees (extended)

- **No proprietary scoring formulas, no proprietary policy bodies, and no
  vector payloads** in the public envelope. Use opaque `scoring_profile`
  identifiers, `policy_hash`, `embedding_hash`, and safe summaries.
- **No raw clinical payloads or model transcripts** in examples or
  accepted subtrees; the validator and `scripts/release_safety_scan.py`
  enforce hygiene.
- **Vendor-neutral compute trace.** `compute_trace` is intentionally
  compatible with the [OpenTelemetry](https://opentelemetry.io/) trace /
  metric / log model so external backends can ingest GalloDoc traces
  without GalloDoc consumers depending on any vendor.
- **Vendor-neutral SBOM.** `artifact_bom` field shapes overlap with
  [SPDX](https://spdx.dev/) and [CycloneDX](https://cyclonedx.org/) so
  external SBOMs can map in losslessly. The package itself ships no live
  vulnerability database.
- **Vendor-neutral policy.** `policy_governance` is engine-neutral —
  implementations may use [OPA / Rego](https://www.openpolicyagent.org/),
  CEL, or a custom JSON rule engine. The envelope records hashes,
  condition summaries, and outcomes only.

## Migration

Nothing to migrate. v2.0 envelopes are v1.x envelopes with optional
top-level blocks added.

To begin emitting v2.0 blocks from your own pipeline:

1. Keep producing the v1.0 envelope and any v1.1–v1.6 blocks you already
   emit.
2. Add only the v2.0 blocks you have data for. Empty/absent blocks are
   the safe default.
3. Use the per-block slugs from the table above for `schema_version`.
4. Run the validator and `scripts/release_safety_scan.py` on your output.

## Acceptance

- v1.0–v1.6 examples still validate. ✅
- v2.0 reference example validates. ✅
- Release safety scan passes (run
  `python3 scripts/release_safety_scan.py`).
- Tests pass (run `python3 -m pytest tests -q`).
- Wheel builds (run `python3 -m build`).

## Install

```bash
pip install gallodoc==2.0.0   # when published
# or, for the latest in-source RC:
pip install -e .
```

## Next

- v2.0.x point releases will harden individual block validators and add
  per-block negative-test fixtures without changing field shapes.
- v2.1 will add reference SDK helpers for emitting `compute_trace` from
  OpenTelemetry exporters and importing `artifact_bom` from SPDX /
  CycloneDX without runtime dependencies on either format.
