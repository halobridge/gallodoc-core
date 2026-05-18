# GalloDoc Core v3 — Master Spec

**Status:** active
**Python package version:** `3.0.0`
**Schema family:** `gallodoc-core/v3`
**Envelope identifier constant:** `schema_version: "gallodoc-core/v3"`

GalloDoc Core v3 is the **Portable Operational Intelligence Document
Standard.** It consolidates the five overlapping surfaces that accumulated
across v1.0–v2.1 (`trust_score`/`trust_decision`, `relationships`/
`document_relationships`, `lifecycle.stages[]`/`workflow_execution.workflow_steps[]`,
`source`/`connector_lineage`, plus the `extensions.halobridge.<block>`
double-emission for v1.2–v1.6 compliance blocks) into a single coherent
envelope shape. The v1 schema and validator stay parallel-supported for a
**6-month deprecation window** beginning `2026-05-16`.

> v3 is not "frozen." Stability is described concretely: required sections
> will not be removed or renamed without a v4 envelope; new optional blocks
> land additively. See [§v1-to-v3 compatibility](#9-v1-to-v3-compatibility)
> and [§v1 supersession — three explicit moves](#10-v1-supersession--three-explicit-moves).

This document is the **canonical end-to-end reference** for v3. It is
designed to be read in roughly 20 minutes. For the eight area specs that
back this overview, see [§13 — area specs](#13-area-specs).

---

## 0. Reading guide

| If you are… | Start here |
|---|---|
| A consumer evaluating GalloDoc | [§v3 at a glance](#v3-at-a-glance) and [§14 — how to use the v3.0 surface](#14-how-to-use-the-v30-surface) |
| A producer building a connector | [§13.2 — connector SDK](#132-open-connector-sdk-codex-03), then [`docs/positioning/connector-guide.md`](../positioning/connector-guide.md) |
| An ops engineer running the linker | [§13.3 — linker](#133-gallounit-keyed-linker-codex-04), then [`docs/positioning/linker-guide.md`](../positioning/linker-guide.md) |
| An ML engineer reproducing `gallodoc-bge-m3-v1` | [§13.6 — training lab](#136-embedder-training-lab-codex-06) → [§13.7 — trained embedder](#137-trained-embedder-v1-codex-07), then [`docs/positioning/training-guide.md`](../positioning/training-guide.md) |
| A migration owner moving v1 envelopes to v3 | [`docs/migration/v1-to-v3.md`](../migration/v1-to-v3.md) |
| A compliance / privacy lead | [§8 — privacy invariants](#8-privacy-invariants), then [`docs/positioning/privacy-and-governance-guide.md`](../positioning/privacy-and-governance-guide.md) |

## v3 at a glance

| Property | Value |
|---|---|
| Schema family | `gallodoc-core/v3` (const) |
| Required top-level sections | **18** (one more than v1) |
| Optional top-level sections | **23** |
| New top-level blocks vs v1 | `trust` (required), `federation` (optional) |
| Backward compat | v1 envelopes continue to validate under the parallel v1 validator for 6 months |
| Migration helper | `gallodoc.projection.migrate_v1_to_v3(envelope)` |
| New CLI surfaces | `gallodoc connector convert`, `gallodoc semantic embed`, `gallodoc training export-pairs`, `gallodoc federation match`, `gallodoc aibi plan` |
| Release safety gate | `make release-gate` — see [§15](#15-release-safety-gate) |

---

## 1. Envelope identifier

```
schema_version: "gallodoc-core/v3"   // const
```

The schema file ships at
[`gallodoc/schema/gallodoc-core-v3.schema.json`](../../gallodoc/schema/gallodoc-core-v3.schema.json).
The v1 schema file ([`gallodoc-core-v1.schema.json`](../../gallodoc/schema/gallodoc-core-v1.schema.json))
remains on disk and unchanged.

`gallodoc.schema.load_schema()` accepts an explicit
`version` argument and dispatches between the two files. The default is
`"gallodoc-core/v3"`. `gallodoc.validation.validate_envelope()` dispatches
based on the envelope's declared `schema_version`.

---

## 2. The 18 required v3 top-level sections

Source: [`docs/v3-design/05_v3_master_spec_outline.md §2`](../../../../docs/v3-design/05_v3_master_spec_outline.md).
v1 had 17 required sections; v3 adds **one** new required section: the
consolidated `trust` block.

| # | Section | Source | Notes |
|---|---|---|---|
| 1 | `schema_version` | v1 | Const `gallodoc-core/v3`. |
| 2 | `identity` | v1 + cleanup | `gallodoc_id` only — drop `package_id` alias. |
| 3 | `source` | v1 + v2.0 `connector_lineage` | Subsumes `connector_source` and `connector_lineage`. |
| 4 | `purpose` | v1 | Unchanged. |
| 5 | `lifecycle` | v1 + v2.0 `workflow_execution` | Unified timeline; `lifecycle.stages[]` is canonical; optional per-step `workflow_steps[]` carried over from v2.0. |
| 6 | `activity` | v1 | Unchanged (PII-stripped access log). |
| 7 | `relationships` | v2.0 `document_relationships` shape + `status` enum + `discovered_by` | Now an object with `relationships[]` array, NOT a bare array as in v1. |
| 8 | `evidence` | v1 | Unchanged. |
| 9 | `validations` | v1 | Unchanged (contradictions + packet findings + model disagreements). |
| 10 | `security` | v1 | Unchanged. |
| 11 | `exports` | v1 | Unchanged. |
| 12 | `extensions` | v1 | Unchanged opaque namespace, but with `extensions.halobridge.<known_block>` bans (see §3). |
| 13 | `ai_usage` | v1 Amendment 1 | Unchanged. |
| 14 | `gallounits` | v1 Amendment 1 | Unchanged structurally in v3.0. Optional sibling array `gallounits.embeddings[]` ships in Codex 05 — see [`gallodoc-core-v3-embeddings.md`](gallodoc-core-v3-embeddings.md). |
| 15 | `certification` | v1 Amendment 1 | Unchanged. |
| 16 | `gstp` | v1 Amendment 1 | Unchanged. |
| 17 | `truth_ledger` | v1 Amendment 1 | Unchanged. |
| 18 | `trust` | **NEW.** v1 `trust_score` ⊕ v1.5 `trust_decision` | **Consolidated flat block.** See [§4 trust block shape](#4-the-flat-trust-block). |

---

## 3. The 23 optional v3 top-level sections

| Section | Source | Why optional |
|---|---|---|
| `policy_governance` | v2.0 | Q6 verification: platform builder partial. Stays optional in v3.0; see [v3.1 promotion checklist](../../../../docs/v3-design/05_v3_master_spec_outline.md). |
| `access_control` | v2.0 | Q6 verification: platform builder is a pure stub. Stays optional in v3.0; see [v3.1 promotion checklist](../../../../docs/v3-design/05_v3_master_spec_outline.md). |
| `certifier` | v1 Amendment 1 | Used when a domain authority signs. |
| `execution_governance` | v1.1 | Used when AI/tool/agent execution is in scope. |
| `consent_ledger` | v1.2 | Used in regulated verticals. |
| `chain_of_custody` | v1.2 | Used when evidence handling matters. |
| `human_decisions` | v1.2 | Used when reviewer decisions are recorded. |
| `attestations` | v1.2 | Used for attestation records. |
| `redaction_manifest` | v1.2 | Used when redaction policies are applied. |
| `evidence_quality` | v1.2 | Used for evidence scoring. |
| `data_residency` | v1.3 | Used for residency-bound deployments. |
| `training_permissions` | v1.3 | Used when training consent is tracked. |
| `model_risk` | v1.3 | Used for model risk classification. |
| `retention_status` | v1.3 | Used for retention policy. |
| `agent_observability` | v1.4 | Used for agent tracing. |
| `agent_supply_chain_security` | v1.6 | Used for agent supply-chain scans. |
| `vector_context` | v2.0 | Used when retrieval indexes ship with the envelope. |
| `temporal_versions` | v2.0 | Used when versioning/replay is recorded. |
| `human_review` | v2.0 | Used when review actions are recorded. |
| `workflow_execution` | v2.0 | Used when richer-than-`lifecycle` per-step data is needed. |
| `compute_trace` | v2.0 | Used when OpenTelemetry-style spans are recorded. |
| `artifact_bom` | v2.0 | Used when SPDX/CycloneDX-compatible BOM ships. |
| `query_access` | v2.0 | Used when saved queries / query receipts / query permissions ship. |
| `federation` | **v3 NEW** | Cross-tenant matching policy + receipts. Key reserved here; full sub-schema ships in prompt 08. |

> Note: the table above shows 24 entries; `trust_decision` (v1.5) is not
> in the list — it has been superseded by the consolidated required `trust`
> block in §2. Counting `federation` plus the 22 non-`trust_decision`
> carryovers yields the 23 optional sections promised in
> [`docs/v3-design/05_v3_master_spec_outline.md §2`](../../../../docs/v3-design/05_v3_master_spec_outline.md).

### v3.1 promotion forward-reference

`policy_governance` and `access_control` are tracked against the v3.1
promotion checklist in
[`docs/v3-design/05_v3_master_spec_outline.md §2`](../../../../docs/v3-design/05_v3_master_spec_outline.md).
Both must satisfy four conditions before being promoted to required:
non-stub builder data on the happy path, an open-source reference
implementation, a v3.0→v3.1 envelope migration test, and exercise of the
validator's per-block forbidden-key set on real data.

---

## 4. The flat `trust` block

Per [Decision 2 in `docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md):
consumer queries against a v3 envelope tend to read across the score /
decision boundary; flat keys avoid forcing every reader to navigate
`trust.decision.gates[]` for what is conceptually a single trust surface.

```json
{
  "trust": {
    "schema_version": "gallodoc.trust.v3.0",
    "components": [],              // from v1 trust_score.components
    "drivers": [],                 // from v1 trust_score.drivers
    "blockers": [],                // from v1 trust_score.blockers
    "warnings": [],                // from v1 trust_score.warnings
    "decision_gates": [],          // from v1.5 trust_decision.decision_gates
    "policy_outcomes": [],         // from v1.5 trust_decision.policy_outcomes
    "action_recommendations": [],  // from v1.5 trust_decision.action_recommendations
    "decision_receipts": []        // from v1.5 trust_decision.decision_receipts
  }
}
```

Sub-array item shapes are ported verbatim from v1
([`gallodoc-core-v1.schema.json`](../../gallodoc/schema/gallodoc-core-v1.schema.json):322-335
for `trust_score.*`) and v1.5
([`gallodoc-core-v1.schema.json`](../../gallodoc/schema/gallodoc-core-v1.schema.json):1037-1241
for `trust_decision.*`), rooted under `trust` instead of `trust_score` /
`trust_decision`.

**Forbidden:** nested `trust.score` or `trust.decision` objects. The v3
validator rejects either (catches accidental carry-overs from v1.5 by tools
that haven't been upgraded — see [§validator rules](#7-v3-validator-rules)).

---

## 5. The extended `relationships` block

v3 uses the v2.0 `document_relationships` shape verbatim at the new
top-level key `relationships`. Two field additions per entry:

| Field | Type | Notes |
|---|---|---|
| `status` | closed enum `suggested \| confirmed \| rejected` | v2.0 already allowed `suggested`; v3 makes the enum explicit and closed. Default for human-authored entries is `confirmed`. |
| `discovered_by` | string (required) | Producer identifier — e.g. `"human_review"`, `"gallodoc-linker/3.0.0"`, `"connector:invoice_stub"`. |

The v3 `relationships` block is a single object with a `relationships[]`
array (matching the v2.0 `document_relationships.relationships[]` shape),
**not** a bare array as in v1. v1's slim bare-array `relationships` is
dropped.

Per [Decision 3](../../../../docs/v3-design/07_decisions.md): the
deterministic linker writes candidates directly into `relationships` with
`status: "suggested"` and `discovered_by: "gallodoc-linker/<version>"`.
A v3 validator rule pins linker entries to `suggested` at validation time
(see §7 rule 1).

---

## 6. Other consolidated sections

### `source` — absorbs v2.0 `connector_lineage`

Union of v1 `source` fields plus a new optional sub-block
`source.connector_lineage = {connector_sources[], sync_runs[], record_receipts[]}`
carrying the v2.0 `connector_lineage` shape.

### `lifecycle` — absorbs v2.0 `workflow_execution.workflow_steps[]`

v1 fields preserved. New optional `lifecycle.workflow_steps[]` carrying the
v2.0 `workflow_execution.workflow_steps[]` shape (per-step
`input_hash` / `output_hash` plus `step_id`, `step_name`, `step_type`,
`status`, `duration_ms`, `error_summary`).

The standalone v2.0 `workflow_execution` block remains optional in v3
(carries the richer `workflow_runs[]` shape that is broader than `lifecycle`).

### `federation` — new optional top-level block

Per [Decision 4](../../../../docs/v3-design/07_decisions.md): federation is
a first-class top-level optional block, **not** split across
`access_control` + `policy_governance`, and **never** under
`extensions.halobridge.*`. v3.0 ships the full sub-schema in Codex 08; see
[§13.8 — federation](#138-federation-codex-08).

---

## 7. v3 validator rules

The v3 validator runs the same structural checks the v1 validator does
against the v3 schema, carries forward all v1.x / v2.0 public-safety rules
(`execution_governance`, v1.2 compliance, `trust_decision` carryover, v2.0
forbidden-key scans), and adds **five** additive rules (3 from Codex 01 +
2 from Codex 08):

1. **Linker entries pin to `suggested`.** Any entry in
   `relationships.relationships[]` whose `discovered_by` matches
   `re.compile(r".*linker.*", re.IGNORECASE)` AND has
   `status != "suggested"` is rejected. The linker cannot accidentally
   publish a confirmed relationship; promotion happens via
   `relationships.relationship_decisions[]` and is recorded explicitly.

2. **Banned `extensions.halobridge.<known_block>` keys.** Any of the
   following keys under `extensions.halobridge` is rejected:

   ```
   consent_ledger, chain_of_custody, human_decisions, attestations,
   redaction_manifest, evidence_quality, data_residency, training_permissions,
   model_risk, retention_status, agent_observability, trust_decision,
   agent_supply_chain_security, federation
   ```

   (13 v1.2–v1.6 compliance block names plus `federation` per Decision 4
   — 14 names total.) These blocks live at top level only in v3; the
   migration helper in Codex 02 strips them on upgrade.

3. **Trust block is flat.** If the envelope contains
   `trust.score` or `trust.decision` as a nested object, the envelope is
   rejected. Catches v1.5 carry-overs.

4. **`federation.cross_tenant_policy.sharing_scope` is closed.** Must be
   one of `tenant_private | fingerprint_only | semantic_only |
   trusted_exchange | disabled`.

5. **`federation.matching_receipts[].raw_data_exposed` must be `false`.**
   v3.0 forbids cross-tenant raw-data exposure. The flag is reserved for
   v4 under more rigorous controls.

---

## 8. Privacy invariants

Carried forward unchanged from v2.0. The per-block `FORBIDDEN_KEYS` sets
defined in
[`gallodoc/validation/__init__.py:220-345`](../../gallodoc/validation/__init__.py)
remain the contract for the v3 validator. New blocks added in this
release inherit the v2.0 base set and add their own.

No raw PHI, PII, credentials, tenant boundary IDs, prompt text, response
text, access tokens, raw vectors, or signing keys may appear in committed
envelopes or examples. Synthetic data only.

`gallodoc.projection.safety.assert_no_enterprise_leakage(envelope)` is
the single canonical privacy assertion, called from the release safety
gate (§15) and CI workflow (§12).

---

## 9. v1-to-v3 compatibility

### Parallel-validator dispatch

`gallodoc.validation.validate_envelope(envelope)` reads `envelope["schema_version"]`
and dispatches:

- `"gallodoc-core/v1"` → `_validate_v1()` — preserves every existing v1 rule
  unchanged.
- `"gallodoc-core/v3"` → `_validate_v3()` — applies the v3 structural check
  plus the additive rules above plus all carried-forward
  public-safety rules.
- anything else (including missing `schema_version`) → returns
  `valid=False` with an `"unknown schema version"` issue.

### Deprecation window

**6 months** from `2026-05-16` (per the recommendation in
[`docs/v3-design/05_v3_master_spec_outline.md §1`](../../../../docs/v3-design/05_v3_master_spec_outline.md)
sub-decision). During the window:

- Every v1 / v1.x / v2.0 envelope continues to validate under the v1
  validator unchanged.
- New consumers default to v3.
- The v1 schema file stays on disk indefinitely (it's only JSON).
- The migration helper (Codex 02 — see [§13.1](#131-reference-projector--migration-helper-codex-02))
  converts v1 envelopes to v3 envelopes.

### Migration helper

`gallodoc.projection.migrate_v1_to_v3(envelope)` is the single supported
v1 → v3 upgrade path. It is idempotent. It performs three transforms:

1. Flattens `trust_score.*` and `trust_decision.*` into the v3 `trust.*`
   layout (Decision 2).
2. Rewrites `relationships` from v1's bare array into the v3 object
   shape, injecting `status` (defaults to `confirmed` for human-authored
   entries) and `discovered_by` (Decision 3).
3. Promotes any `extensions.halobridge.<v1.2–v1.6 compliance block>` to
   the top level, de-duplicating against any pre-existing top-level
   counterpart (Decision 4, Q5 fix).

See [`docs/migration/v1-to-v3.md`](../migration/v1-to-v3.md) for a worked
example with a before/after envelope.

---

## 10. v1 supersession — three explicit moves

Per [Decision 1](../../../../docs/v3-design/07_decisions.md):

1. **[`docs/GALLODOC_CORE_V1_FROZEN.md`](../GALLODOC_CORE_V1_FROZEN.md)
   carries a "Superseded by v3" preamble.** Names v3 as the successor,
   declares the 6-month parallel-validation deprecation window, notes the
   original freeze commitment is honored within v1's scope.

2. **`pyproject.toml` classifier bumped from `3 - Alpha` to `4 - Beta`.**
   The Alpha classifier was what made revving v1 possible; if v3 keeps
   it, the implicit message is "we'll do this again." Bumping to Beta is
   the only credible accompaniment to the rev.

3. **"Frozen" framing dropped from v3 release notes.** Stability is
   described in concrete terms (required sections will not be removed or
   renamed without a v4 envelope; new optional blocks land additively) —
   not in absolute language ("frozen") that the team has already shown it
   can flip.

The release safety gate (§15) verifies all three supersession artifacts
on every release-branch push; the gate refuses to pass if any artifact is
missing.

---

## 11. The five locked decisions

The full statements + rationale live in
[`docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md).
This is the one-paragraph summary for each.

| # | Decision | Summary |
|---|---|---|
| **D1** | Envelope strategy: rev to `gallodoc-core/v3` | v1 had five overlapping surfaces and no real consumers; revving is safe. The `Development Status :: 3 - Alpha` classifier removed the structural argument against it. Three supersession moves preserve credibility: FROZEN-doc preamble, classifier bump to 4-Beta, "frozen" framing dropped. 6-month parallel v1 validator window. See [§10](#10-v1-supersession--three-explicit-moves). |
| **D2** | Flat `trust` block | Consumer queries read across the score/decision boundary; flat keys avoid forcing every reader to navigate `trust.decision.gates[]`. The v3 validator rejects nested `trust.score` / `trust.decision` (rule 3). The migrator emits flat keys directly. See [§4](#4-the-flat-trust-block). |
| **D3** | Linker target: `relationships` with `status: "suggested"` | The deterministic linker writes directly into `relationships` with `status: "suggested"` and `discovered_by: "gallodoc-linker/<version>"`. No parallel staging block. Validator rule 1 pins linker entries to `suggested` at validation time. Promotion to `confirmed`/`rejected` happens via `apply_relationship_decision()`, which appends a `relationship_decisions[]` record. See [§5](#5-the-extended-relationships-block) and [§13.3](#133-gallounit-keyed-linker-codex-04). |
| **D4** | `federation` as a top-level optional block | Tenant-level matching is conceptually distinct from per-actor `access_control` and per-policy `policy_governance`. `extensions.halobridge.federation` is rejected (rule 2, key `federation` added to the banned set). See [§13.8](#138-federation-codex-08). |
| **D5** | `::semantic_intent` GalloMarkdown block | RELATION_INTENT semantics (e.g. `invoice_to_employee_approver`) live in a new `::semantic_intent` block. The linker reads matching intent as a relationship-discovery signal at weight 0.6; the trained embedder learns relationship intent from the same block. See [§13.3](#133-gallounit-keyed-linker-codex-04) and [`docs/specs/gallodoc-semantic-intent-v3.md`](gallodoc-semantic-intent-v3.md). |

---

## 12. The eight Codex contributions (one paragraph each)

The v3.0 surface was produced by ten Codex prompts; Codex 01 + Codex 10
are scoped to envelope + release plumbing, and the eight area specs below
describe the rest.

### 12.1 Codex 01 — envelope consolidation

Cuts the v3 schema file, the parallel-validator dispatch, the three
additive validator rules (D2/D3 enforcement, banned `extensions.halobridge.*`
keys), and the master spec scaffold. The `pyproject.toml` classifier bumps
to `4 - Beta`; `GALLODOC_CORE_VERSION` bumps to `gallodoc-core/v3`; and
the `GALLODOC_CORE_V1_FROZEN.md` preamble is added.

### 12.2 Codex 02 — reference projector + migration helper

Ships `gallodoc.projection.project_to_open_core` (the open-source
reference projector — closes the largest open-source adoption gap),
`gallodoc.projection.migrate_v1_to_v3` (idempotent, one-shot v1 → v3
upgrade), `gallodoc.projection.forbidden.EXTENSIONS_HALOBRIDGE_BANNED`
(canonical 14-name set), and `gallodoc.projection.safety.assert_no_enterprise_leakage`
(privacy assertion used by the release safety gate). Spec at
[`gallodoc-core-v3-reference-projector.md`](gallodoc-core-v3-reference-projector.md).

### 12.3 Codex 03 — open connector SDK

Ships `gallodoc.connectors` with the `ConnectorSource` / `ConnectorRecord` /
`GalloDocConnector` / `ConnectorRunReceipt` interfaces, five starter
connectors (`generic_json`, `csv_row`, `pdf_file_metadata`,
`salesforce_account_stub`, `invoice_stub`), and the
`gallodoc connector convert` CLI. Each connector emits a valid v3
envelope with populated `source.connector_lineage`. Spec at
[`gallodoc-core-v3-connector-sdk.md`](gallodoc-core-v3-connector-sdk.md).

### 12.4 Codex 04 — GalloUnit-keyed linker

Ships `gallodoc.linking` — deterministic relationship discovery with no
ML dependencies. Reads GalloUnit hashes, truth_ledger claim IDs,
`::semantic_intent` values, and source IDs as signals. 8-signal weighted
scoring with capped shared-evidence contributions. Linker output writes
into `relationships.relationships[]` with `status: "suggested"` and
`discovered_by: "gallodoc-linker/<version>"`.
`apply_relationship_decision()` flips entries to `confirmed`/`rejected`
and appends a `relationship_decisions[]` record. Adds the 8th
GalloMarkdown block type `::semantic_intent` (D5). Spec at
[`gallodoc-core-v3-linker.md`](gallodoc-core-v3-linker.md) and vocabulary
at [`gallodoc-semantic-intent-v3.md`](gallodoc-semantic-intent-v3.md).

### 12.5 Codex 05 — GalloUnit embeddings adapter

Ships `gallodoc.semantic.embeddings` with `EmbeddingAdapter` interface,
the `EmbeddingRecord` shape, the closed 6-value `PURPOSE_ENUM`, three
starter adapters (`local_stub` deterministic default; `bge_m3` and
`sentence_transformers` lazy-imported under the `[semantic]` extra), and
the `gallodoc semantic embed` CLI. Embeddings attach to
`gallounits.embeddings[]` as a sibling array. Raw vectors never ship by
default; the `--include-vector` flag raises `EnterpriseLeakageError`
unless `safety_profile.raw_vectors_stored == true`. Spec at
[`gallodoc-core-v3-embeddings.md`](gallodoc-core-v3-embeddings.md).

### 12.6 Codex 06 — embedder training lab

Ships `gallodoc.training` with `TrainingPair` schema, closed 3-value
`LABEL_ENUM`, `extract_pairs_from_envelope(s)`, `generate_hard_negatives`
(4 strategies), `split_train_dev_test` (seed=42), and `assert_pairs_clean`
(privacy gate — no skip path; export aborts on leak). Positives come from
`relationships.relationships[]` entries with `status: "confirmed"` AND a
matching `relationship_decisions[]` record. CLI:
`gallodoc training export-pairs`. Spec at
[`gallodoc-core-v3-training-lab.md`](gallodoc-core-v3-training-lab.md).

### 12.7 Codex 07 — trained embedder v1

Ships the **training recipe** for `gallodoc-bge-m3-v1` at
`scripts/train_gallodoc_embedder.py` (base model: `BAAI/bge-m3`;
contrastive pair learning; multi-profile output with 6 heads, one per
`PURPOSE_ENUM` value). **No model weights are committed** — the recipe is
open-source, the weights live externally (HF Hub / S3 / internal
registry). `--mode tiny` runs on CI fixtures in seconds, CPU-OK. The
evaluation harness produces `eval_report.json` with the seven required
metrics (recall@5, precision@5, MRR, false-positive rate,
per-relationship-type accuracy, `semantic_intent_accuracy`,
`human_review_agreement_rate`). D5 filter: training pairs must have a
resolved `semantic_intent` on source AND target to count as positives.
Spec at [`gallodoc-core-v3-trained-embedder.md`](gallodoc-core-v3-trained-embedder.md).

### 12.8 Codex 08 — federation block

Ships the full v3 `federation` top-level block (D4) with
`CrossTenantPolicy`, the `intersect` "most-restrictive-wins" function,
the 5-scope enum (`tenant_private` → `disabled`), the signal admissibility
matrix, `apply_federation_policy`, `build_matching_receipts`, and
`cross_tenant_link`. Tightens the v3 schema sub-shape (was previously
loose) and adds validator rules 4 and 5. CLI:
`gallodoc federation match`. Spec at
[`gallodoc-core-v3-federation.md`](gallodoc-core-v3-federation.md).

### 12.9 Codex 09 — NL→GQL planner

Ships `gallodoc.aibi` with the `QueryPlan` data model, 6 safe filter
primitives (`eq`, `in_`, `has_token`, `has_relationship`, `time_range`,
`confidence_at_least`), 5 query templates (`relationship_query`,
`semantic_similarity_query`, `operational_timeline_query`,
`evidence_chain_query`, `trust_query`), and a federation-aware policy_check
generator. **Planner only** — no executor. **No raw SQL ever** —
`assert_plan_is_safe` rejects any string containing
`SELECT`/`INSERT`/`UPDATE`/`DELETE`/semicolons/backticks. D2/D3/D4
enforced: filters reference flat trust paths; relationship filters default
to `status: "confirmed"`; cross-tenant queries emit
`federation_intersection` policy_checks. CLI: `gallodoc aibi plan`. Spec
at [`gallodoc-core-v3-aibi-planner.md`](gallodoc-core-v3-aibi-planner.md).

### 12.10 Codex 10 — v3 master release

This prompt. Finalizes the master spec, writes the migration guide and
release notes, ships the 7 positioning docs, builds the
`scripts/release_safety_gate.py` (12 checks + 3 supersession-artifact
checks), adds the `Makefile`, deletes the v2.x `release_safety_scan.py`,
backfills v2.0 / v2.1 CHANGELOG entries, and pins the v3.0.0 tag-ready
state. See [§15 — release safety gate](#15-release-safety-gate) and
[`RELEASE_NOTES_3.0.0.md`](../../RELEASE_NOTES_3.0.0.md).

---

## 13. Area specs

The full area specs live in `docs/specs/`. The map below cross-references
each area spec to the Codex that produced it and to the audience-targeted
positioning doc.

### 13.1 Reference projector + migration helper (Codex 02)

- Spec: [`gallodoc-core-v3-reference-projector.md`](gallodoc-core-v3-reference-projector.md)
- Positioning: [`docs/positioning/privacy-and-governance-guide.md`](../positioning/privacy-and-governance-guide.md)
- Migration guide: [`docs/migration/v1-to-v3.md`](../migration/v1-to-v3.md)

### 13.2 Open connector SDK (Codex 03)

- Spec: [`gallodoc-core-v3-connector-sdk.md`](gallodoc-core-v3-connector-sdk.md)
- Positioning: [`docs/positioning/connector-guide.md`](../positioning/connector-guide.md)

### 13.3 GalloUnit-keyed linker (Codex 04)

- Spec: [`gallodoc-core-v3-linker.md`](gallodoc-core-v3-linker.md)
- Vocabulary: [`gallodoc-semantic-intent-v3.md`](gallodoc-semantic-intent-v3.md)
- Positioning: [`docs/positioning/linker-guide.md`](../positioning/linker-guide.md)

### 13.4 (reserved — no Codex 04.5)

### 13.5 GalloUnit embeddings adapter (Codex 05)

- Spec: [`gallodoc-core-v3-embeddings.md`](gallodoc-core-v3-embeddings.md)
- Positioning: [`docs/positioning/semantic-encoder-guide.md`](../positioning/semantic-encoder-guide.md)

### 13.6 Embedder training lab (Codex 06)

- Spec: [`gallodoc-core-v3-training-lab.md`](gallodoc-core-v3-training-lab.md)
- Positioning: [`docs/positioning/semantic-encoder-guide.md`](../positioning/semantic-encoder-guide.md)
  and [`docs/positioning/training-guide.md`](../positioning/training-guide.md)

### 13.7 Trained embedder v1 (Codex 07)

- Spec: [`gallodoc-core-v3-trained-embedder.md`](gallodoc-core-v3-trained-embedder.md)
- Positioning: [`docs/positioning/training-guide.md`](../positioning/training-guide.md)

### 13.8 Federation (Codex 08)

- Spec: [`gallodoc-core-v3-federation.md`](gallodoc-core-v3-federation.md)
- Positioning: [`docs/positioning/privacy-and-governance-guide.md`](../positioning/privacy-and-governance-guide.md)

### 13.9 NL→GQL planner (Codex 09)

- Spec: [`gallodoc-core-v3-aibi-planner.md`](gallodoc-core-v3-aibi-planner.md)
- Positioning: [`docs/positioning/what-is-gallodoc.md`](../positioning/what-is-gallodoc.md)

---

## 14. How to use the v3.0 surface

The 5-minute install → first envelope → first query flow.

### 14.1 Install

```bash
pip install gallodoc                    # core; zero hard dependencies
pip install gallodoc[schema]            # adds jsonschema for full Draft-2020-12 checks
pip install gallodoc[semantic]          # adds sentence-transformers + numpy for the bge_m3/sentence_transformers embedding adapters
pip install gallodoc[schema,semantic]   # both
```

### 14.2 First envelope (one shell command)

```bash
gallodoc connector convert \
  --connector generic_json \
  --input my_data.json \
  --out env.gdoc.json
```

This emits a valid `gallodoc-core/v3` envelope with `source.connector_lineage`
populated. Validate it:

```bash
gallodoc validate env.gdoc.json
# prints: "<file>: OK (schema_version=gallodoc-core/v3)"
```

### 14.3 Attach embeddings (optional)

```bash
gallodoc semantic embed env.gdoc.json \
  --adapter local_stub \
  --purpose document_retrieval \
  --out env_with_embeddings.gdoc.json
```

`local_stub` is deterministic and ships in core. For real embeddings,
install `gallodoc[semantic]` and pass `--adapter bge_m3`.

### 14.4 Link two envelopes

```python
from gallodoc.linking import link, write_into_envelope
import json

source = json.load(open("env_a.gdoc.json"))
candidates = [json.load(open("env_b.gdoc.json"))]
output = link(source, candidates)
write_into_envelope(source, output)
json.dump(source, open("env_a_linked.gdoc.json", "w"), indent=2)
```

Linker entries land with `status: "suggested"`. Use
`gallodoc.linking.apply_relationship_decision()` to confirm or reject.

### 14.5 First NL → query plan

```bash
gallodoc aibi plan "show invoices linked to John" --envelope env_a_linked.gdoc.json
# emits a QueryPlan JSON to stdout
```

Pass `--check-only` to validate the plan without printing it. Pass
`--out plan.json` to write to disk.

### 14.6 Migrate a v1 envelope

```python
from gallodoc.projection import migrate_v1_to_v3
from gallodoc.validation import validate_envelope
import json

v1_env = json.load(open("legacy.json"))
v3_env = migrate_v1_to_v3(v1_env)
assert validate_envelope(v3_env).valid
json.dump(v3_env, open("upgraded.gdoc.json", "w"), indent=2)
```

See [`docs/migration/v1-to-v3.md`](../migration/v1-to-v3.md) for the full
worked example.

---

## 15. Release safety gate

The canonical release-readiness signal:

```bash
cd opensource/gallodoc-core
make release-gate
cat release_safety_report.json
```

The gate exits 0 iff every check passes, every supersession artifact is
true, and `summary.violations == []`. It runs **12 checks**:

| # | Check | What it verifies |
|---|---|---|
| 1 | `v3_examples_validate` | Every v3 example envelope validates under the v3 validator. |
| 2 | `v1_examples_still_validate` | Every v1 example validates under the parallel v1 validator. |
| 3 | `v2_0_examples_still_validate` | Every v2.0 example validates. |
| 4 | `v2_1_examples_still_validate` | Every v2.1 example validates. |
| 5 | `privacy_scan` | `assert_no_enterprise_leakage` on every example. |
| 6 | `forbidden_subtree_scan` | No example has a banned key under `extensions.halobridge.*`. |
| 7 | `extensions_halobridge_known_blocks_absent` | Stronger phrasing of #6 for clarity. |
| 8 | `trust_block_flat_only` | No example has `trust.score` or `trust.decision` as nested dicts. |
| 9 | `linker_entries_pinned_to_suggested` | D3 — every linker-discovered relationship has `status: "suggested"` or a matching `relationship_decisions[]` record. |
| 10 | `no_model_weights_committed` | No `*.bin/*.safetensors/*.pt/*.ckpt/*.onnx/*.gguf` under the package tree. |
| 11 | `reference_projector_idempotent` | `project_to_open_core(project_to_open_core(env)) == project_to_open_core(env)`. |
| 12 | `migration_v1_to_v3_round_trip` | `validate_envelope(migrate_v1_to_v3(v1_env)).valid is True` for every v1 example. |

Plus three supersession-artifact checks (Decision 1):

- `frozen_doc_preamble_present` — `docs/GALLODOC_CORE_V1_FROZEN.md`
  contains "Superseded by v3" in the first 30 lines.
- `pyproject_classifier_bumped` — `pyproject.toml` contains
  `"Development Status :: 4 - Beta"`.
- `frozen_framing_dropped_from_release_notes` —
  `RELEASE_NOTES_3.0.0.md` does NOT describe v3 as "frozen".

See the full output shape in
[`docs/v3-design/RELEASE_RUNBOOK.md §4`](../../../../docs/v3-design/RELEASE_RUNBOOK.md).
