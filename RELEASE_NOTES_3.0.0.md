# GalloDoc Core 3.0.0 — release notes

**Date:** 2026-05-17
**Status:** **Development Status :: 4 - Beta** in `pyproject.toml`
**Schema family:** `gallodoc-core/v3` (const)
**Backward compatibility:** the parallel v1 validator stays supported for
**6 months** beginning 2026-05-17.

GalloDoc Core 3.0.0 ships the **Portable Operational Intelligence
Document Standard**. v3 consolidates the five overlapping surfaces that
accumulated across v1.0–v2.1 (trust score / trust decision; relationships
vs document_relationships; lifecycle vs workflow_execution; source vs
connector_lineage; the `extensions.halobridge.<block>` double-emission)
into a single coherent envelope shape, adds the new
`federation` and `trust` blocks, and ships the open-source GalloUnit
linker, the embeddings adapter pipeline, the embedder training lab, the
trained `gallodoc-bge-m3-v1` recipe, the federation block, and the
NL→GQL planner.

The 5-minute install + first envelope demo:

```bash
pip install gallodoc
gallodoc connector convert --connector generic_json --input my.json --out env.gdoc.json
gallodoc validate env.gdoc.json
gallodoc aibi plan "show invoices linked to John" --envelope env.gdoc.json
```

---

## Stability commitments

v3.0 is **Development Status :: 4 - Beta**. Stability is described
concretely:

- **Required sections will not be removed or renamed without a v4
  envelope.** The 18 required top-level sections (`schema_version`,
  `identity`, `source`, `purpose`, `lifecycle`, `activity`,
  `relationships`, `evidence`, `validations`, `security`, `exports`,
  `extensions`, `ai_usage`, `gallounits`, `certification`, `gstp`,
  `truth_ledger`, `trust`) are contract.
- **New optional blocks land additively.** v3.x can extend the optional
  set; existing consumers continue to validate.
- **The parallel v1 validator stays for 6 months beginning 2026-05-17.**
  After 2026-11-16 the v1 validator may be removed in a v3.x release;
  the v1 schema file stays on disk indefinitely.
- **Migration to Development Status :: 5 - Production/Stable** happens
  when the v3.1 promotion checklist (in
  [`docs/v3-design/05_v3_master_spec_outline.md §2`](../../docs/v3-design/05_v3_master_spec_outline.md))
  passes — that requires `policy_governance` and `access_control` to be
  promoted from optional to required with non-stub builder data and an
  open-source reference implementation on the happy path.

---

## What ships

### Codex 01 — envelope consolidation

- `gallodoc-core/v3` JSON Schema at
  [`gallodoc/schema/gallodoc-core-v3.schema.json`](gallodoc/schema/gallodoc-core-v3.schema.json),
  shipping alongside the unchanged v1 schema file.
- Dual-validator dispatch in `gallodoc.validation.validate_envelope`:
  v1 envelopes route to `_validate_v1`; v3 envelopes route to
  `_validate_v3`. Same dispatch in `validate_with_jsonschema`.
- Three additive v3 validator rules: linker-discovered relationships
  pin to `status: "suggested"`; banned `extensions.halobridge.<known_block>`
  for 14 names; nested `trust.score` / `trust.decision` rejected.
- 18 required + 23 optional top-level sections. v1's 17 required → v3's
  18 required (added: consolidated `trust`). v3.0 keeps
  `policy_governance` and `access_control` optional per the Q6
  verification finding.
- `relationships` is now an object containing a `relationships[]`
  array (was a bare array in v1). Each entry requires the closed
  `status` enum (`suggested | confirmed | rejected`) and a
  `discovered_by` string.
- `source` absorbs the v2.0 `connector_lineage` shape as an optional
  `source.connector_lineage` sub-block.
- `lifecycle` absorbs the v2.0 `workflow_execution.workflow_steps[]`
  shape as an optional `lifecycle.workflow_steps[]` array.
- New optional top-level `federation` block (Decision 4). Full
  sub-schema in Codex 08.
- `gallodoc.schema.load_schema()` accepts an explicit `version`
  argument; default `"gallodoc-core/v3"`. Pass
  `version="gallodoc-core/v1"` for the legacy schema.
- `GALLODOC_CORE_VERSION` (in `gallodoc/__init__.py`) bumped to
  `"gallodoc-core/v3"`. Python `__version__` bumped to `"3.0.0"`.

### Codex 02 — reference projector + migration helper

- `gallodoc.projection.project_to_open_core` — open-source reference
  projector. Idempotent.
- `gallodoc.projection.migrate_v1_to_v3` — one-shot v1 → v3 migration
  helper (three transforms: flat trust, relationship status injection,
  v1.2–v1.6 block promotion). Idempotent.
- `gallodoc.projection.forbidden.EXTENSIONS_HALOBRIDGE_BANNED` — the
  canonical 14-name set used by validator + projector + migrator.
- `gallodoc.projection.safety.assert_no_enterprise_leakage` — privacy
  assertion baked into the release safety gate.

### Codex 03 — open connector SDK

- `gallodoc.connectors` package with `ConnectorSource`,
  `ConnectorRecord`, `GalloDocConnector`, `ConnectorRunReceipt`
  interfaces.
- Five starter connectors: `generic_json`, `csv_row`,
  `pdf_file_metadata`, `salesforce_account_stub`, `invoice_stub`.
- New CLI: `gallodoc connector convert --connector <slug> --input <path> --out <path>`.

### Codex 04 — GalloUnit-keyed linker

- `gallodoc.linking` package with deterministic relationship discovery
  — no ML dependencies. Reads GalloUnit hashes, truth_ledger claim
  IDs, `::semantic_intent` values, and source IDs as signals.
- 8-signal weighted scoring with capped shared-evidence contributions.
- `link(source_envelope, candidate_envelopes)` →
  `LinkerOutput`. Every candidate emitted with `status: "suggested"`
  and `discovered_by: "gallodoc-linker/3.0.0"`.
- `write_into_envelope` and `apply_relationship_decision` helpers.
- 8th GalloMarkdown block type `::semantic_intent` (Decision 5);
  vocabulary at
  [`docs/specs/gallodoc-semantic-intent-v3.md`](docs/specs/gallodoc-semantic-intent-v3.md).

### Codex 05 — GalloUnit embeddings adapter

- `gallodoc.semantic.embeddings` with `EmbeddingAdapter` interface,
  `EmbeddingRecord` shape, closed 6-value `PURPOSE_ENUM`.
- Three starter adapters: `local_stub` (default, deterministic);
  `bge_m3` and `sentence_transformers` (lazy-imported under the
  `[semantic]` extra).
- Raw vectors never ship by default. `--include-vector` flag raises
  `EnterpriseLeakageError` unless
  `safety_profile.raw_vectors_stored == true`.
- New CLI: `gallodoc semantic embed`.

### Codex 06 — embedder training lab

- `gallodoc.training` with `TrainingPair` schema, closed 3-value
  `LABEL_ENUM`, pair extraction, hard-negative generation (4
  strategies), deterministic train/dev/test splitter, and privacy
  scan baked in (`assert_pairs_clean`).
- Positives come from `relationships.relationships[]` entries with
  `status: "confirmed"` AND a matching `relationship_decisions[]`
  record (Decision 3).
- New CLI: `gallodoc training export-pairs`.

### Codex 07 — trained embedder v1

- Training recipe `scripts/train_gallodoc_embedder.py`. Base model:
  `BAAI/bge-m3`. Contrastive pair learning. Multi-profile output
  (6 heads, one per `PURPOSE_ENUM` value).
- **No model weights committed.** The recipe is open-source; the
  weights live externally.
- `--mode tiny` for CI: runs on fixtures in seconds, CPU-OK.
- Evaluation harness `scripts/evaluate_gallodoc_embedder.py` produces
  `eval_report.json` with `recall_at_5`, `precision_at_5`, `mrr`,
  `false_positive_rate`, `per_relationship_type_accuracy`,
  `semantic_intent_accuracy`, `human_review_agreement_rate`.
- Decision 5 filter: training pairs must have a resolved
  `semantic_intent` on source AND target to count as positives.
- `GalloDocBgeM3V1EmbeddingAdapter` — new adapter slug
  `gallodoc_bge_m3_v1`.

### Codex 08 — federation block

- New optional top-level `federation` block (Decision 4). Never under
  `extensions.halobridge.*`.
- `gallodoc.federation` with `CrossTenantPolicy`, `intersect`
  (most-restrictive-wins), `is_cross_tenant_match_permitted`,
  `apply_federation_policy`, `build_matching_receipts`,
  `cross_tenant_link`.
- Sharing scopes: `tenant_private`, `fingerprint_only`,
  `semantic_only`, `trusted_exchange`, `disabled`.
- Two validator rules: `federation.cross_tenant_policy.sharing_scope`
  closed enum; `federation.matching_receipts[].raw_data_exposed` must
  be `false`.
- New CLI: `gallodoc federation match`.

### Codex 09 — NL→GQL planner

- `gallodoc.aibi` with `QueryPlan` data model, 6 safe filter
  primitives, 5 query templates, and federation-aware policy_check
  generator.
- **Planner only** — no executor.
- **No raw SQL ever.** `assert_plan_is_safe` rejects any string
  containing `SELECT`/`INSERT`/`UPDATE`/`DELETE`/semicolons/backticks.
- New CLI: `gallodoc aibi plan`.

### Codex 10 — v3 master release

This release. Finalized master spec, migration guide, 7 positioning
docs, release safety gate
([`scripts/release_safety_gate.py`](scripts/release_safety_gate.py)
with 12 checks + 3 supersession-artifact checks), the `Makefile`,
v2.0/v2.1 CHANGELOG backfill, and the end-to-end demo at
`examples/v3_0/full_operational_intelligence_reference/`.

---

## Breaking changes

| Change | Migration |
|---|---|
| 18 required top-level sections (was 17 in v1) | Run `gallodoc.projection.migrate_v1_to_v3(envelope)`. The migrator injects a flat `trust` block if neither `trust_score` nor `trust_decision` are present in the v1 envelope. |
| `relationships` is now an object containing a `relationships[]` array (was a bare array in v1) | `migrate_v1_to_v3` converts the shape automatically. Each entry gains `status` (default `"confirmed"`) and `discovered_by` (`"v1_migration"` for migrated entries). |
| `trust_score` + `trust_decision` collapsed into flat `trust` block | `migrate_v1_to_v3` merges both into `trust.*` arrays. Nested `trust.score` / `trust.decision` objects are rejected by the v3 validator. |
| `extensions.halobridge.<known_block>` is banned for 14 names (13 v1.2–v1.6 compliance blocks + `federation`) | `migrate_v1_to_v3` promotes the 13 compliance blocks to top level; `federation` is v3-new and shouldn't exist under `extensions.halobridge`. |
| `Development Status` classifier bumped from `3 - Alpha` to `4 - Beta` | Informational. Tools that filter by classifier will see the new value. |

See [`docs/migration/v1-to-v3.md`](docs/migration/v1-to-v3.md) for the
full migration walkthrough with a worked example.

---

## Upgrade path

```python
import json
from gallodoc.projection import migrate_v1_to_v3
from gallodoc.validation import validate_envelope

with open("legacy_v1.json") as fh:
    v1 = json.load(fh)

v3 = migrate_v1_to_v3(v1)
assert validate_envelope(v3).valid
json.dump(v3, open("upgraded.gdoc.json", "w"), indent=2)
```

For more detail see
[`docs/migration/v1-to-v3.md`](docs/migration/v1-to-v3.md).

---

## Supersession of v1

Per Decision 1 (see
[`docs/v3-design/07_decisions.md`](../../docs/v3-design/07_decisions.md))
three explicit moves accompany the v3 release:

1. [`docs/GALLODOC_CORE_V1_FROZEN.md`](docs/GALLODOC_CORE_V1_FROZEN.md)
   carries a "Superseded by v3" preamble.
2. `pyproject.toml` classifier moved from `3 - Alpha` to `4 - Beta`.
3. v3.0 does not describe itself in absolute language. The "frozen"
   framing that v1 used is not repeated for v3 — stability is described
   concretely in the section above.

The release safety gate verifies all three supersession artifacts on
every release-branch push; the gate refuses to pass if any artifact is
missing.

---

## Verification

The release safety gate (`make release-gate`) ran clean against this
release. Every check passed; every supersession artifact present;
`summary.violations == []`. See
[`docs/v3-design/RELEASE_RUNBOOK.md §4`](../../docs/v3-design/RELEASE_RUNBOOK.md)
for the canonical output shape.

---

## Further reading

- [`docs/specs/gallodoc-core-v3-master-spec.md`](docs/specs/gallodoc-core-v3-master-spec.md)
  — the master spec (reads end-to-end in ~20 minutes).
- [`docs/migration/v1-to-v3.md`](docs/migration/v1-to-v3.md) — full
  migration guide.
- [`docs/positioning/what-is-gallodoc.md`](docs/positioning/what-is-gallodoc.md)
  — what GalloDoc is, in 90 seconds.
- [`CHANGELOG.md`](CHANGELOG.md) — version history.
