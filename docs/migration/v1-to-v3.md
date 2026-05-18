# Migrating from GalloDoc Core v1 to v3

**Audience:** producers and consumers with existing v1.x envelopes who want
to adopt v3. This guide is self-contained — a v1 consumer should be able
to upgrade following only this document, with no chat access to the
maintainer.

**TL;DR:** call `gallodoc.projection.migrate_v1_to_v3(envelope)`. It is
idempotent. The v3 validator then accepts the output.

---

## 1. What's new per release

### v2.0 — 11 optional platform blocks

v2.0 added 11 optional top-level blocks: `query_access`, `vector_context`,
`document_relationships`, `temporal_versions`, `policy_governance`,
`access_control`, `human_review`, `workflow_execution`, `connector_lineage`,
`compute_trace`, `artifact_bom`. The schema family remained
`gallodoc-core/v1` — these were additive amendments, not a rev.

### v2.1 — GalloMarkdown layer

v2.1 added the `GalloMarkdown` authoring surface (7 block types:
`::gallodoc`, `::artifact`, `::evidence`, `::trust`, `::decision`,
`::policy`, `::agent_security`) and a `gallodoc validate` multi-file
invocation. Still `gallodoc-core/v1`.

### v3.0 — envelope rev + consolidation

v3.0 reps `schema_version` to `gallodoc-core/v3` and:

- **Consolidates 5 overlapping surfaces** from v1/v1.x/v2.0:
  - `trust_score` ⊕ `trust_decision` → unified flat `trust` block.
  - `relationships` (bare array) ⊕ `document_relationships` → single
    `relationships` object with a `relationships[]` array.
  - `source` ⊕ `connector_lineage` → `source` with an optional
    `source.connector_lineage` sub-block.
  - `lifecycle.stages[]` ⊕ `workflow_execution.workflow_steps[]` →
    `lifecycle` with optional `lifecycle.workflow_steps[]`.
  - The 13 v1.2–v1.6 compliance blocks that were double-emitted under
    `extensions.halobridge.<block>` AND top level → top level only (the
    `extensions.halobridge.<known_block>` surface is now banned).
- **Adds** an 18th required section: the consolidated `trust` block.
- **Adds** an optional top-level `federation` block (Decision 4 — see
  [`docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md)).
- **Adds** the `::semantic_intent` GalloMarkdown block (Decision 5),
  the GalloUnit-keyed linker, the embeddings adapter pipeline, the
  embedder training lab, the trained `gallodoc-bge-m3-v1` embedder, and
  the NL→GQL planner.

---

## 2. Compatibility guarantees

- **v1.x envelopes validate under the parallel v1 validator unchanged.**
  `gallodoc.validation.validate_envelope(envelope)` reads
  `envelope["schema_version"]` and routes:
  - `"gallodoc-core/v1"` → `_validate_v1()` (every rule unchanged).
  - `"gallodoc-core/v3"` → `_validate_v3()`.
  - anything else → `valid=False` with `"unknown schema version"`.
- The v1 schema file
  ([`gallodoc/schema/gallodoc-core-v1.schema.json`](../../gallodoc/schema/gallodoc-core-v1.schema.json))
  stays on disk indefinitely.
- v2.0 / v2.1 envelopes (which still declare `gallodoc-core/v1`)
  continue to validate as v1.x.

---

## 3. Optional adoption path

You do not have to migrate. Producers can stay on v1.x indefinitely
within the deprecation window. New producers should default to v3.

| If you are… | Recommended path |
|---|---|
| Shipping a new envelope today | Default to v3. Use `gallodoc connector convert`. |
| Maintaining v1.x producers with downstream consumers | Stay on v1 until consumers upgrade. Plan v3 migration before 2026-11-16. |
| Consuming envelopes from multiple producers | Accept both. `validate_envelope` dispatches by `schema_version`. |
| Re-emitting envelopes (a projection pipeline) | Migrate inputs to v3 with `migrate_v1_to_v3`, then validate. |

---

## 4. Privacy posture upgrades

v3 tightens the v1.x privacy contract in three concrete ways:

### 4.1 `extensions.halobridge.<known_block>` is banned

v2.0 platforms (notably the HaloBridge projector) were double-emitting
the 13 v1.2–v1.6 compliance blocks under BOTH the top level AND
`extensions.halobridge.<block>`. v3 forbids the latter — these blocks
live at top level only.

Banned keys under `extensions.halobridge`:

```
consent_ledger, chain_of_custody, human_decisions, attestations,
redaction_manifest, evidence_quality, data_residency, training_permissions,
model_risk, retention_status, agent_observability, trust_decision,
agent_supply_chain_security, federation
```

The migration helper promotes these to the top level, de-duplicating
against any pre-existing top-level counterpart. The v3 validator rejects
any surviving instance with a clear error.

### 4.2 Flat `trust` block

The v3 `trust` block is flat — no nested `trust.score.*` /
`trust.decision.*`. The v3 validator rejects nested objects under either
key. Migration is handled automatically by `migrate_v1_to_v3`.

### 4.3 Release-gate-enforced safety scan

`gallodoc.projection.safety.assert_no_enterprise_leakage(envelope)` is
baked into the release safety gate (check #5 — see
[`docs/v3-design/RELEASE_RUNBOOK.md §4`](../../../../docs/v3-design/RELEASE_RUNBOOK.md)).
The scan walks every committed example envelope and refuses to pass if
it finds:

- Platform-internal keys (`policy_formula`, `halobridge_internal`,
  `__internal__`).
- Surviving `extensions.halobridge.<banned>` keys.
- SSN-like / MRN-like / private-key-shaped strings.

---

## 5. The 6-month deprecation window

The parallel v1 validator is supported for **6 months** beginning
`2026-05-17` (the v3.0.0 release date). After **2026-11-16**, the v1
validator may be removed in a v3.x release.

During the window:

- Every v1 / v1.x / v2.0 envelope continues to validate under the v1
  validator unchanged.
- New consumers default to v3.
- The v1 schema file stays on disk indefinitely (it's only JSON; even
  after the validator is removed, the schema file can stay).
- `migrate_v1_to_v3` is the supported one-shot upgrade path.

Removing the v1 validator is a soft milestone — driven by adoption
metrics. The schema sub-decision documented in
[`docs/v3-design/05_v3_master_spec_outline.md §1`](../../../../docs/v3-design/05_v3_master_spec_outline.md)
allows extension upward if real-world consumers materialize and need
more time.

---

## 6. Step-by-step migration

The three-line happy path:

```python
import json
from gallodoc.projection import migrate_v1_to_v3
from gallodoc.validation import validate_envelope

with open("legacy_v1.json") as fh:
    v1_env = json.load(fh)

v3_env = migrate_v1_to_v3(v1_env)
result = validate_envelope(v3_env)
assert result.valid, result.issues
```

That's it. `migrate_v1_to_v3` is idempotent: calling it on an envelope
that's already v3 is a no-op.

### What the migrator does

1. **Bumps `schema_version`** to `gallodoc-core/v3`.
2. **Flattens `trust`** — merges `trust_score.{components,drivers,blockers,warnings}`
   and v1.5 `trust_decision.{gates,policy_outcomes,action_recommendations,decision_receipts}`
   into the flat `trust.{components,drivers,blockers,warnings,decision_gates,policy_outcomes,action_recommendations,decision_receipts}`
   arrays. Sets `trust.schema_version = "gallodoc.trust.v3.0"`. Deletes
   the source `trust_score` and `trust_decision` keys. Also drains any
   `extensions.halobridge.trust_decision` (Q5 double-emission carryover)
   into the same flat block. If neither source exists, injects an
   empty-but-shaped flat trust block so the migrated envelope satisfies
   v3's required-sections rule.
3. **Rewrites `relationships`** — converts v1's bare-array shape
   (`relationships: [...]`) into the v3 object shape
   (`relationships: {relationships: [...]}`). For each entry:
   - Renames `source_document_id` → `source_document_ref` and
     `target_document_id` → `target_document_ref` (v3 field naming).
   - Sets `status = "confirmed"` if missing.
   - Sets `discovered_by = "v1_migration"` if missing — preserves the
     audit trail that the entry came from a v1 envelope, not a human.
4. **Promotes 13 compliance blocks** — anything under
   `extensions.halobridge.<block>` matching the
   v1.2–v1.6 set is moved to the top level. If a top-level counterpart
   already exists, the migration prefers the top-level value and discards
   the duplicate from `extensions.halobridge`. (See
   [Q5 in `docs/v3-design/02_gallomvp_divergence.md §5.1`](../../../../docs/v3-design/02_gallomvp_divergence.md)
   for background on the double-emission bug being fixed.)

### Optional follow-up

If the migrated envelope is going downstream into the projector
(open-source consumers), pipe it through `project_to_open_core`:

```python
from gallodoc.projection import project_to_open_core

clean = project_to_open_core(v3_env)
```

`project_to_open_core` is also idempotent. The release safety gate
verifies this (check #11 — `reference_projector_idempotent`).

---

## 7. Worked example

### Before — a minimal v1 envelope

```json
{
  "schema_version": "gallodoc-core/v1",
  "identity": { "gallodoc_id": "doc-001", "title": "Sample" },
  "source": { "source_system": "upload_portal", "source_kind": "document" },
  "purpose": { "primary_intent": "review" },
  "lifecycle": { "stages": [] },
  "activity": { "events": [] },
  "relationships": [
    {
      "relationship_id": "rel-001",
      "source_document_id": "doc-001",
      "target_document_id": "doc-002",
      "relationship_type": "related_to"
    }
  ],
  "evidence": { "items": [] },
  "validations": { "contradictions": [] },
  "security": {},
  "exports": [],
  "extensions": {
    "halobridge": {
      "consent_ledger": {
        "schema_version": "gallodoc.consent_ledger.v1.2",
        "consents": []
      }
    }
  },
  "ai_usage": { "events": [] },
  "gallounits": { "units": [] },
  "certification": {},
  "gstp": {},
  "truth_ledger": { "claims": [] },
  "trust_score": {
    "components": [{"name": "completeness", "value": 0.9}],
    "drivers": [],
    "blockers": [],
    "warnings": []
  },
  "trust_decision": {
    "gates": [{"gate_id": "g1", "outcome": "pass"}],
    "policy_outcomes": [],
    "action_recommendations": [],
    "decision_receipts": []
  }
}
```

### After — `migrate_v1_to_v3(envelope)` output

```json
{
  "schema_version": "gallodoc-core/v3",
  "identity": { "gallodoc_id": "doc-001", "title": "Sample" },
  "source": { "source_system": "upload_portal", "source_kind": "document" },
  "purpose": { "primary_intent": "review" },
  "lifecycle": { "stages": [] },
  "activity": { "events": [] },
  "relationships": {
    "relationships": [
      {
        "relationship_id": "rel-001",
        "source_document_ref": "doc-001",
        "target_document_ref": "doc-002",
        "relationship_type": "related_to",
        "status": "confirmed",
        "discovered_by": "v1_migration"
      }
    ]
  },
  "evidence": { "items": [] },
  "validations": { "contradictions": [] },
  "security": {},
  "exports": [],
  "extensions": {},
  "ai_usage": { "events": [] },
  "gallounits": { "units": [] },
  "certification": {},
  "gstp": {},
  "truth_ledger": { "claims": [] },
  "trust": {
    "schema_version": "gallodoc.trust.v3.0",
    "components": [{"name": "completeness", "value": 0.9}],
    "drivers": [],
    "blockers": [],
    "warnings": [],
    "decision_gates": [{"gate_id": "g1", "outcome": "pass"}],
    "policy_outcomes": [],
    "action_recommendations": [],
    "decision_receipts": []
  },
  "consent_ledger": {
    "schema_version": "gallodoc.consent_ledger.v1.2",
    "consents": []
  }
}
```

Differences:

- `schema_version` bumped to `gallodoc-core/v3`.
- `relationships` is an object containing a `relationships[]` array
  (was a bare array in v1).
- Each relationship gained `status: "confirmed"` and
  `discovered_by: "v1_migration"` (audit trail).
- Field names migrated: `source_document_id` → `source_document_ref`,
  `target_document_id` → `target_document_ref`.
- `trust_score` + `trust_decision` collapsed into a single flat
  `trust` block.
- `extensions.halobridge.consent_ledger` promoted to top-level
  `consent_ledger`.

The migrated envelope validates cleanly under the v3 validator.

---

## 8. Round-trip test

`migrate_v1_to_v3` is verified by the release safety gate's check #12
(`migration_v1_to_v3_round_trip`): for every v1 example in the repo,

```python
validate_envelope(migrate_v1_to_v3(v1_env)).valid is True
```

If you have a v1 envelope that fails to round-trip, please open an
issue with the reproducer envelope (stripped of any sensitive data) at
<https://github.com/halobridge/gallodoc/issues>.

---

## 9. Further reading

- [`docs/specs/gallodoc-core-v3-master-spec.md`](../specs/gallodoc-core-v3-master-spec.md)
  — full v3 spec.
- [`docs/specs/gallodoc-core-v3-reference-projector.md`](../specs/gallodoc-core-v3-reference-projector.md)
  — projector + migrator contract.
- [`RELEASE_NOTES_3.0.0.md`](../../RELEASE_NOTES_3.0.0.md) — what ships
  in v3.0.0.
- [`docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md)
  — the five locked design decisions behind v3.
