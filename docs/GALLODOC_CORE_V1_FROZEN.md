# GalloDoc Core v1 — FROZEN

> **Superseded by v3.** `gallodoc-core/v3` is the active envelope. The v1
> schema and validator stay parallel-supported for a 6-month deprecation
> window beginning 2026-05-16. The original freeze commitment is honored
> within v1's scope — v1 envelopes will continue to validate under the v1
> validator unchanged for the duration of the window. See
> [CHANGELOG.md](../../CHANGELOG.md) for the v3.0.0 entry.

**Status:** FROZEN
**Frozen at:** 2026-05-01
**Frozen version:** `gallodoc-core/v1`
**Authoritative constant:** `mvp_core.services.gallodoc_open_core_projection_service.GALLODOC_CORE_VERSION`
**Schema:** [`docs/specs/gallodoc-core-v1.schema.json`](gallodoc-core-v1.schema.json)
**Field map:** [`docs/specs/gallodoc-core-v1-field-map.csv`](gallodoc-core-v1-field-map.csv)
**Companion specs:** [`gstp-v1.md`](gstp-v1.md), [`gallounits-v1.md`](gallounits-v1.md)
**Freeze audit:** [`docs/architecture/GALLODOC_CORE_V1_FREEZE_AUDIT.md`](../architecture/GALLODOC_CORE_V1_FREEZE_AUDIT.md)

This document declares GalloDoc Core v1 frozen. Every downstream consumer (the
open-core distribution, the GSTP signer, the audit tooling, third-party
integrators) MUST treat the schema and the projected envelope shape as a stable
contract from this point forward.

## Required top-level sections (frozen)

These 17 keys are required at the top level of every GalloDoc Core v1
envelope. Removing or renaming any of them is a breaking change and requires
v2.

| # | Section | Notes |
|---|---|---|
| 1 | `schema_version` | Const `gallodoc-core/v1`. |
| 2 | `identity` | Document identity + envelope hash. |
| 3 | `source` | Connector / system origin. |
| 4 | `purpose` | Workflow intent. |
| 5 | `lifecycle` | Stage timeline + provenance chain. |
| 6 | `activity` | Public access trail. |
| 7 | `relationships` | Document-to-document edges. |
| 8 | `evidence` | Bounded reference list. |
| 9 | `validations` | Contradictions + packet findings + model disagreements. |
| 10 | `security` | PHI / encryption posture summary. |
| 11 | `exports` | Bounded export descriptors. |
| 12 | `extensions` | Vendor extension namespace. |
| 13 | `ai_usage` | Provider / model / token / cost / latency ledger (Amendment 1). |
| 14 | `gallounits` | Model-agnostic semantic evidence units (Amendment 1). |
| 15 | `certification` | Human-only, evidence-backed attestation (Amendment 1). |
| 16 | `gstp` | GalloDoc Secure Transport Package references (Amendment 1). |
| 17 | `truth_ledger` | Immutable claim/event history references (Amendment 1). |

Optional sections (`certifier`, `media`, `connector_source`, `packets`,
`contradictions`, `external_evidence`, `model_verification`, `trust_score`,
`policy`, `review`, `corrections`, `retention`, `lineage`, `metrics`) are also
frozen — once present they may not be renamed or retyped.

## Stability rules

1. **No field removals.** Once a field path appears in the field map under
   `frozen_v1`, it MUST keep working forever in v1. Removing it is a breaking
   change that requires v2.
2. **No renames.** Field names, enum values, and section keys are frozen.
   Renaming a field (even if the type is unchanged) is a breaking change.
3. **No type changes.** Once a field is declared `string`, it is always
   `string`. Widening a number to `string` or vice versa is a breaking
   change.
4. **No enum-value removals or repurposings.** Enums (e.g.
   `purpose.primary_intent`, `security.phi_risk_level`,
   `security.encryption_policy_status`, `certification.status`,
   `gstp.status`, `truth_ledger.truth_state`) gain new values **only** in v2.
   Removing or repurposing an existing value is breaking.
5. **Additive-only changes.** New optional sections and new optional fields
   inside existing sections are allowed in v1 patch releases provided they
   default to safe empty values and the projection always emits them. Adding
   a *required* field to an existing section is breaking.
6. **Breaking changes require v2.** Anything that violates rules 1-5 lands in
   `gallodoc-core/v2` and ships under a new `schema_version` constant. v1
   consumers continue to validate against v1 indefinitely.
7. **Vendor extensions live under `extensions.<vendor>.*`.** The v1 schema
   does not constrain inner shapes of extension subkeys, but vendors MUST
   keep their own subschemas backwards-compatible.
8. **Projection is the only sanctioned channel.** Open-core consumers receive
   GalloDoc envelopes only through
   `mvp_core.services.gallodoc_open_core_projection_service.project_gallodoc_to_open_core`
   (or the equivalent open-source `gallodoc.validation.project` helper). Direct
   re-emission of a HaloBridge `gallodoc/v1` envelope as `gallodoc-core/v1` is
   not supported.
9. **Privacy invariants are part of the freeze.** Raw prompts, raw responses,
   raw model payloads, signing keys, raw signatures, credential secrets, full
   policy formulas, raw prior-claim values, IP/session hashes, OAuth tokens,
   and vault refs are NEVER projected to open core. The forbidden-key list in
   the projection service is part of the v1 contract.
10. **The `frozen` flag in the schema is authoritative.** The schema JSON
    carries `"frozen": true`, `"frozen_version": "gallodoc-core/v1"`, and
    `"frozen_at": "2026-05-01"`. Tooling that wants to verify "this is v1"
    can rely on those fields.

## How v2 will be introduced

When Amendment 2 (or later) collects enough breaking changes, we publish a
new schema (`docs/specs/gallodoc-core-v2.schema.json`) with a new constant
(`gallodoc-core/v2`). v1 stays in this repo for the freeze window
(target: at least 24 months). Both projections coexist; consumers pin the
version they want.

## Verifying the freeze in CI

Two automated checks enforce this freeze:

- `python3 -m pytest mvp_core/tests/test_gallodoc_core_v1_freeze_audit.py -q`
  — includes explicit tests that fail when any required top-level section is
  removed from `REQUIRED_V1_SECTIONS` or from the schema JSON, when
  `GALLODOC_CORE_VERSION` drifts away from `gallodoc-core/v1`, or when the
  schema's `frozen` flag is missing or false.
- `python3 manage.py audit_gallodoc_core_v1 --strict` — the management
  command exits 1 on any regression.

Both must pass before any change to GalloDoc Core lands on `main`.
