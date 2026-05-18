# Migration examples (v3.0)

Walkthrough of `gallodoc.projection.project_to_open_core` and
`gallodoc.projection.migrate_v1_to_v3` on four synthetic envelopes.

All data is synthetic: `example.com` emails, fake UUIDs, placeholder
sha256 hashes. No real PHI/PII, no real account numbers.

## The four files

| File | Demonstrates |
|---|---|
| `producer_input_full.json` | Producer-side input (v1 shape) carrying ALL the patterns the projector handles, including platform-leakage patterns (`policy_formula`, `halobridge_internal`, `__internal__`), the Q5 double-emission bug (`extensions.halobridge.consent_ledger` AND top-level `consent_ledger`), v1 bare-array relationships, and nested v1 `trust_score` / `trust_decision`. |
| `projected_output_full.json` | Exact output of `project_to_open_core(producer_input_full)`. Shows what survives the open-source projector. |
| `v1_to_v3_input.json` | Clean v1.x envelope (no platform leakage) with a v1 bare-array `relationships` list and `extensions.halobridge.attestations`. No `trust_score` / `trust_decision` populated (the migrator injects an empty flat trust block). |
| `v1_to_v3_output.json` | Exact output of `migrate_v1_to_v3(v1_to_v3_input)`. Validates as v3 via `validate_envelope`. |

## What `producer_input_full` -> `projected_output_full` demonstrates

The open-source `project_to_open_core` is the inner sanitizer. It:

1. **Migrates v1 -> v3 internally.** The input declares
   `schema_version: "gallodoc-core/v1"`; the projector calls
   `migrate_v1_to_v3` first, then projects.
2. **Strips banned `extensions.halobridge.<known_block>` keys.** The
   `extensions.halobridge.consent_ledger` payload is gone; the
   top-level `consent_ledger` survives (the Q5 fix — top-level is the
   canonical home).
3. **Strips v1.x / v2.0 forbidden key names recursively.** None are
   present in this input, but the strip would apply to keys like
   `password`, `raw_prompt`, `api_key`, etc. anywhere in the tree.
4. **Converts the v1 bare-array `relationships` to v3 object shape**
   with `status: "confirmed"` and `discovered_by: "v1_migration"`
   injected on every entry (Decision 3). Renames v1
   `source_document_id` / `target_document_id` to v3
   `source_document_ref` / `target_document_ref`.
5. **Merges v1 `trust_score` / `trust_decision` into a flat `trust`
   block** (Decision 2). No nested `trust.score` or `trust.decision`.

**But the projected output STILL contains:**

- `activity.latest_events[0].metadata.policy_formula`
- `activity.latest_events[0].metadata.halobridge_internal`
- `activity.latest_events[0].metadata.__internal__`

That's the layering contract. The open-source projector intentionally
does NOT strip platform-private patterns. The platform projector
([`mvp_core/services/gallodoc_open_core_projection_service.py`](../../../../../mvp_core/services/gallodoc_open_core_projection_service.py))
layers its own stripping on top by calling
`project_to_open_core` first, then applying the platform-specific
filter.

`assert_no_enterprise_leakage(projected_output_full)` will raise
because of those three surviving keys — that's the safety net for
production releases.

## What `v1_to_v3_input` -> `v1_to_v3_output` demonstrates

The `migrate_v1_to_v3` function in isolation, on clean v1 data:

1. **Flat trust** — no `trust_score` / `trust_decision` source; the
   migrator injects an empty flat trust block with the 8 same-level
   arrays. v3 requires the trust block.
2. **Relationship status injection** — v1 bare-array `relationships`
   converts to v3 object shape; each entry gets the v3-required
   `status` and `discovered_by` defaults. `rel-0002` keeps its
   pre-existing `status: "rejected"` (existing values are not
   overwritten).
3. **Q5 fix** — `extensions.halobridge.attestations` promotes to
   top-level `attestations`; the extensions copy is dropped; the
   `halobridge` namespace becomes empty and is removed from
   `extensions`.

The migrated output validates under the v3 validator
(`validate_envelope(v1_to_v3_output).valid == True`).

## Round-trip tests

`tests/v3_0/projection/test_migration_examples.py` asserts that:

- `project_to_open_core(producer_input_full) == projected_output_full`
- `migrate_v1_to_v3(v1_to_v3_input) == v1_to_v3_output`

So any change to the projector or migrator that drifts the output of
either example fails CI.
