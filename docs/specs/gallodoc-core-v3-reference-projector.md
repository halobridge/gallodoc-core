# GalloDoc Core v3 — Reference projector + v1→v3 migration helper

**Status:** active. Ships in `gallodoc` 3.0 alongside the v3 envelope (see
[`gallodoc-core-v3-master-spec.md`](gallodoc-core-v3-master-spec.md)). Anchors:
the five locked decisions in
[`docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md).
Closes the largest open-source adoption gap surfaced in
[`docs/v3-design/02_gallomvp_divergence.md §7`](../../../../docs/v3-design/02_gallomvp_divergence.md).
Concurrently fixes the v1.2–v1.6 double-emission bug surfaced in §5.1 of the
same document (Q5 verification).

## Overview

`gallodoc.projection` is the open-source reference projector + migration
helper for the `gallodoc-core/v3` envelope.

Before v3, every producer of GalloDoc envelopes had to write its own
field-stripping, enum-coercion, and array-cardinality logic — or it emitted
invalid envelopes. The HaloBridge platform had 1038 disciplined lines of
projection code at
[`mvp_core/services/gallodoc_open_core_projection_service.py`](../../../../mvp_core/services/gallodoc_open_core_projection_service.py);
none of it was reusable by third-party producers.

The `gallodoc.projection` package ships:

- `project_to_open_core(envelope)` — recursive sanitizer that produces a
  v3-shaped envelope. Drops the open-source-known forbidden key names,
  removes banned `extensions.halobridge.<known_block>` keys, coerces enums
  to safe defaults, and caps array cardinality.
- `migrate_v1_to_v3(envelope)` — one-shot upgrade that applies the three
  v1→v3 transforms (flat trust, relationship status injection, Q5 fix).
- `projection.forbidden.EXTENSIONS_HALOBRIDGE_BANNED` — canonical 14-name
  set used by the validator, projector, migrator, and safety helper.
- `projection.safety.assert_no_enterprise_leakage(envelope)` — privacy
  assertion for v3 envelopes. Used by the v3-release.yml CI privacy scan
  and (in prompt 10) by `scripts/release_safety_gate.py`.

This is the open-source reference. The platform projector wraps it and
layers its own platform-specific stripping (`policy_formula`,
`halobridge_internal`, `__internal__`) on top — those patterns stay
platform-side per
[`RELEASE_RUNBOOK.md §7`](../../../../docs/operations/RELEASE_RUNBOOK.md)
and are NOT stripped by the open-source projector.

## Function contract: `project_to_open_core`

```python
def project_to_open_core(envelope: dict) -> dict
```

- **Returns:** a v3 envelope. The function never raises. It returns the
  best-effort sanitized result no matter how malformed the input is.
- **`schema_version` handling:** if missing, the projector defaults to
  `"gallodoc-core/v3"`. If the input declares `"gallodoc-core/v1"`, the
  projector internally calls `migrate_v1_to_v3` first, then projects.
- **Enum coercion:** invalid enum values fall back to safe defaults rather
  than raising. The platform projector's leniency tables (around lines 111–162
  of `gallodoc_open_core_projection_service.py`) are the porting source.
- **Array cardinality cap:** every list is capped to 512 items (matching
  the validator's `[:512]` slice pattern in `_scan_v20_block_leaks`).
- **Strip surface (see below)** is applied recursively.

### Strip surface

The open-source projector recursively drops:

1. **Open-source-known forbidden key names.** Every key already in the
   validator's per-block forbidden sets — the v1.x base set
   (`_EXECUTION_GOVERNANCE_FORBIDDEN_KEYS`,
   `_COMPLIANCE_V12_EXTRA_FORBIDDEN_KEYS`, etc.) and the v2.0 base set
   (`_V20_BASE_FORBIDDEN_KEYS` plus the per-block extras). These are the
   keys the validator would already reject; the projector strips them
   pre-emptively so the projected envelope passes validation.
2. **Banned `extensions.halobridge.<known_block>` keys.** The 14 names in
   `EXTENSIONS_HALOBRIDGE_BANNED` (13 v1.2–v1.6 compliance blocks plus
   `federation` per Decision 4). This is the Q5 fix — these blocks must
   live at top level only in v3.

The open-source projector does **NOT** strip:

- `policy_formula`, `policy_expression`, `policy_rule_source` — these are
  platform-private patterns. The HaloBridge projector handles them.
- `halobridge_internal` — vendor-private namespace flag.
- `__internal__` — vendor-private namespace flag.

The platform projector at
[`mvp_core/services/gallodoc_open_core_projection_service.py`](../../../../mvp_core/services/gallodoc_open_core_projection_service.py)
layers those three patterns on top of `project_to_open_core`. This
layering is the contract: a vendor with platform-specific forbidden
patterns extends the open-source projector with its own stripping
pass; the open-source distribution never assumes a particular vendor's
internal taxonomy.

## Function contract: `migrate_v1_to_v3`

```python
def migrate_v1_to_v3(envelope: dict) -> dict
```

- **Returns:** a v3-shaped envelope. `schema_version` is set to
  `"gallodoc-core/v3"` regardless of the input version.
- **Never raises** — already-v3 envelopes pass through unchanged.
- **Idempotent** — see below.

The migrator applies three transforms, in order:

### Transform 1 — Flat trust merge (Decision 2)

If `envelope["trust_score"]` or `envelope["trust_decision"]` exists, the
migrator builds a single flat `trust` block:

```python
{
  "schema_version": "gallodoc.trust.v3.0",
  "components":              [...],   # from trust_score.components
  "drivers":                 [...],   # from trust_score.drivers
  "blockers":                [...],   # from trust_score.blockers
  "warnings":                [...],   # from trust_score.warnings
  "decision_gates":          [...],   # from trust_decision.gates
  "policy_outcomes":         [...],   # from trust_decision.policy_outcomes
  "action_recommendations":  [...],   # from trust_decision.action_recommendations
  "decision_receipts":       [...],   # from trust_decision.decision_receipts
}
```

The eight arrays sit at the same level. No nested `trust.score` or
`trust.decision` is ever produced (per Decision 2 the v3 trust block is
flat — validator rule rejects nested forms).

After the merge the migrator deletes `envelope["trust_score"]` and
`envelope["trust_decision"]`.

### Transform 2 — Relationship status injection (Decision 3)

If `envelope["relationships"]` is a bare list (v1 shape), the migrator
converts it to v3 object shape: `{"relationships": [array], ...}`.
If `envelope["relationships"]["relationships"]` already exists (v2.0
object shape) the migrator leaves the wrapper alone.

For every entry in the array:

- If `status` is missing or empty, set `status = "confirmed"`.
- If `discovered_by` is missing or empty, set
  `discovered_by = "v1_migration"`.
- Existing values are NOT overwritten — if the input has
  `status: "rejected"`, the output keeps `"rejected"`.

The rationale (per Decision 3): pre-existing v1 `relationships[]` entries
were already in the envelope before automated linking existed, so they
are conceptually human-confirmed. The migration preserves prior intent.

### Transform 3 — Q5 fix: promote `extensions.halobridge.<v1.2–v1.6>` to top level

For each name in `V12_V16_COMPLIANCE_BLOCKS` (the 13 v1.2–v1.6
compliance block names — `consent_ledger`, `chain_of_custody`,
`human_decisions`, `attestations`, `redaction_manifest`,
`evidence_quality`, `data_residency`, `training_permissions`,
`model_risk`, `retention_status`, `agent_observability`,
`trust_decision`, `agent_supply_chain_security`):

- If `envelope["extensions"]["halobridge"][name]` exists:
  - If `envelope[name]` also exists at top level (double-emission bug),
    keep the top-level value and delete the extensions copy. (The two
    copies are usually identical; keeping top-level preserves the
    canonical home per the v3 spec.)
  - If `envelope[name]` is missing, copy the extensions content to top
    level, then delete the extensions copy.
- If `extensions.halobridge` ends up empty, drop the `halobridge` key.
- If `extensions` ends up empty, drop the `extensions` key entirely.
  (But if other vendor namespaces remain — `extensions.acme.*` — those
  are preserved.)

Note: `federation` is in `EXTENSIONS_HALOBRIDGE_BANNED` but **not** in
`V12_V16_COMPLIANCE_BLOCKS`. Federation is v3-new (Decision 4) and
shouldn't exist in any v1.x envelope; the validator rejects it under
`extensions.halobridge.*` and the projector strips it, but the migrator
does not attempt to promote it from there.

Note: `trust_decision` is in `V12_V16_COMPLIANCE_BLOCKS` (it is one of
the 13 v1.2–v1.6 amendment block names) but is also the v1.5 source for
Transform 1 (flat trust merge). The migrator folds the content of
`extensions.halobridge.trust_decision` (or any top-level `trust_decision`)
into the v3 flat `trust` block rather than promoting it as a separate
top-level key. The other 12 v1.2–v1.6 blocks are pure top-level
promotions.

### Idempotency

Running `migrate_v1_to_v3(migrate_v1_to_v3(envelope))` produces the same
result as `migrate_v1_to_v3(envelope)`. Why this matters:

- The migrator may run twice if a pipeline retries.
- Mixed-version corpora may contain envelopes that are partially
  migrated (e.g. flat trust but old `extensions.halobridge.consent_ledger`).
- Tests assert idempotency via deep-equality. A second invocation is a
  no-op on the output of a first.

The function must not crash on already-v3 envelopes. An envelope with
`schema_version == "gallodoc-core/v3"` and no v1-shaped surfaces is
returned unchanged (after the `schema_version` set at the end).

## Privacy safety: `assert_no_enterprise_leakage`

```python
def assert_no_enterprise_leakage(envelope: dict) -> None
```

Raises `EnterpriseLeakageError` if the envelope contains:

- Any **platform-internal key name** anywhere in the tree:
  `policy_formula`, `halobridge_internal`, `__internal__`.
- Any **surviving `extensions.halobridge.<known_block>`** key from the
  14-name `EXTENSIONS_HALOBRIDGE_BANNED` set. After a successful
  `project_to_open_core` pass, none of these should remain.
- Any **SSN-like, MRN-like, or private-key-shaped string**
  (`\d{3}-\d{2}-\d{4}`, `MRN[: ]+[A-Z0-9]{6,}`,
  `private_key|signing_key|raw_signature|PRIVATE_PEM`).

This helper is the privacy gate the v3 release CI runs. It is referenced
by:

- `tests/v3_0/projection/test_assert_no_enterprise_leakage.py` for
  regression coverage.
- The forward-referenced `scripts/release_safety_gate.py` shipped in
  prompt 10.
- `.github/workflows/v3-release.yml`, which already imports it with a
  hardcoded-mirror fallback for the period before prompt 10 lands the
  full release-gate script.

## Files

```
opensource/gallodoc-core/
└── gallodoc/
    └── projection/
        ├── __init__.py        # re-exports project_to_open_core, migrate_v1_to_v3
        ├── forbidden.py       # EXTENSIONS_HALOBRIDGE_BANNED + V12_V16_COMPLIANCE_BLOCKS
        ├── projector.py       # project_to_open_core
        ├── migrator.py        # migrate_v1_to_v3
        └── safety.py          # assert_no_enterprise_leakage + EnterpriseLeakageError
```

## Test coverage

`tests/v3_0/projection/` ships:

- Happy path: idempotency of projection; flat-trust merge; relationship
  status injection; Q5 fix promotion (one parametrized test per block in
  `V12_V16_COMPLIANCE_BLOCKS`); migration idempotency; v3 envelopes
  unchanged.
- Negative: `assert_no_enterprise_leakage` raises on each leak shape;
  the projector strips banned-extensions keys but does NOT strip
  platform-private patterns (`policy_formula` etc.); banned keys are
  removed for every name in `EXTENSIONS_HALOBRIDGE_BANNED`; v1 examples
  round-trip through the migrator and re-validate as v3.
- Examples: `tests/v3_0/projection/test_migration_examples.py` asserts
  that the four committed examples in
  [`examples/v3_0/migration/`](../../examples/v3_0/migration/) round-trip
  through the projector and migrator with structural equality.

## Examples

[`examples/v3_0/migration/`](../../examples/v3_0/migration/) ships:

- `producer_input_full.json` — producer-side input (v1 shape) with
  platform leakage patterns populated. Demonstrates the inputs the
  projector handles.
- `projected_output_full.json` — the result of running the open-source
  `project_to_open_core` on the input above. Note that
  `policy_formula`, `halobridge_internal`, `__internal__` are still
  present in the output — the open-source projector does NOT strip
  them; the platform layers that stripping on top.
- `v1_to_v3_input.json` — clean v1.x envelope (no platform leakage)
  with nested trust, pre-existing relationships, and
  `extensions.halobridge.attestations`.
- `v1_to_v3_output.json` — the result of `migrate_v1_to_v3` on the
  input above. Shows the three transforms cleanly.

A walkthrough at [`README.md`](../../examples/v3_0/migration/README.md)
explains what each file demonstrates.

## Cross-references

- Locked decisions: [`docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md)
  (Decisions 1–4 are load-bearing for this spec).
- v3 envelope: [`gallodoc-core-v3-master-spec.md`](gallodoc-core-v3-master-spec.md).
- Q5 bug & adoption gap:
  [`docs/v3-design/02_gallomvp_divergence.md §5.1, §7`](../../../../docs/v3-design/02_gallomvp_divergence.md).
- Platform projector porting source (read-only for this prompt):
  [`mvp_core/services/gallodoc_open_core_projection_service.py`](../../../../mvp_core/services/gallodoc_open_core_projection_service.py).
- Platform-side refactor that wraps `project_to_open_core` as a
  substrate: [`RELEASE_RUNBOOK.md §7`](../../../../docs/operations/RELEASE_RUNBOOK.md)
  (separate PR — out of scope for this prompt).
