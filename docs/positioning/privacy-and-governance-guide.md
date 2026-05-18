# Privacy and governance guide

**Audience:** compliance leads, privacy officers, governance owners
evaluating GalloDoc against regulatory requirements.
**Reading time:** ~7 minutes.
**Companion specs:**
[`docs/specs/gallodoc-core-v3-master-spec.md`](../specs/gallodoc-core-v3-master-spec.md),
[`docs/specs/gallodoc-core-v3-reference-projector.md`](../specs/gallodoc-core-v3-reference-projector.md),
[`docs/specs/gallodoc-core-v3-federation.md`](../specs/gallodoc-core-v3-federation.md).

---

## What v3 promises about your data

| Promise | Mechanism |
|---|---|
| Raw prompts, raw responses, OAuth tokens, API keys, and platform-internal IDs never leave your tenant | `assert_no_enterprise_leakage` + per-block forbidden-key sets; release safety gate check #5 |
| 13 v1.2–v1.6 compliance blocks live at top level only, never duplicated under `extensions.halobridge.*` | `EXTENSIONS_HALOBRIDGE_BANNED` validator rule 2 + migration helper Q5 fix |
| Trust score and trust decision data live in one flat `trust` block — no nested objects | Validator rule 3; migrator transform 1 |
| Linker-discovered relationships start as `suggested` and require explicit human action to become `confirmed` or `rejected` | Validator rule 1 + `apply_relationship_decision` audit trail |
| Cross-tenant relationships respect the most-restrictive policy intersection | `federation.intersect` + validator rules 4–5 |
| No model weights ship in the open-source repo | Release safety gate check #10; CI scan |
| Raw embedding vectors do not ship unless explicitly opted in | `EnterpriseLeakageError` on `--include-vector` without `safety_profile.raw_vectors_stored == true` |
| The release safety gate verifies all 12 invariants on every release-branch push | `make release-gate` + GitHub Actions Job 5 |

---

## The 14 banned `extensions.halobridge.<known_block>` keys

These v1.2–v1.6 compliance blocks live at top level only in v3:

```
consent_ledger, chain_of_custody, human_decisions, attestations,
redaction_manifest, evidence_quality, data_residency, training_permissions,
model_risk, retention_status, agent_observability, trust_decision,
agent_supply_chain_security
```

Plus `federation` (v3-new — never valid under `extensions.halobridge.*`).

If you have v1.x envelopes with these blocks double-emitted, the
migration helper (`gallodoc.projection.migrate_v1_to_v3`) promotes them
to the top level and removes the duplicate.

---

## What the privacy scan catches

`gallodoc.projection.safety.assert_no_enterprise_leakage(envelope)`
walks the envelope and refuses to pass on any of:

| Category | Detection |
|---|---|
| Platform-internal keys | `policy_formula`, `halobridge_internal`, `__internal__` anywhere in the tree |
| Banned `extensions.halobridge.*` keys | Any of the 14 names above as a key under `extensions.halobridge` |
| SSN-like patterns | `\b\d{3}-\d{2}-\d{4}\b` |
| MRN-like patterns | `\bMRN[: ]+[A-Z0-9]{6,}\b` |
| Private-key-shaped strings | `private_key`, `signing_key`, `raw_signature`, `PRIVATE_PEM` |

A failure raises `EnterpriseLeakageError`. The release safety gate
elevates that to a check failure that blocks the release.

---

## Federation — the cross-tenant contract

The new top-level `federation` block carries the producer's
cross-tenant sharing policy. Five scopes, in restrictiveness order:

| Scope | What it permits |
|---|---|
| `tenant_private` (default) | No cross-tenant signal. |
| `fingerprint_only` | Hash-based signals only (text hash, claim ID, projection hash, source record ID, relationship value hash). |
| `semantic_only` | Embedding-profile signals only (semantic intent match, semantic role, evidence ref). |
| `trusted_exchange` | Both signal types. |
| `disabled` | The block is present but cross-tenant matching is off. |

When two tenants attempt a cross-tenant match, the linker calls
`federation.intersect(policy_a, policy_b)` and the **most-restrictive
policy wins**:

| Field | Intersection rule |
|---|---|
| `sharing_scope` | Most restrictive of the two. |
| `requires_review` | `OR` (either side can demand review). |
| `permitted_relationship_types` | Set intersection. |
| Boolean flags (e.g. `allow_pii_signals`) | `AND` (both sides must allow). |
| `matching_receipts[].raw_data_exposed` | Must be `false` in v3.0 (validator rule 5). |

If the intersected scope is `tenant_private` or `disabled`, no match
is admitted regardless of signal strength.

See [`docs/specs/gallodoc-core-v3-federation.md`](../specs/gallodoc-core-v3-federation.md)
for the signal admissibility matrix.

---

## Three privacy posture upgrades vs v2.x

### 1. `extensions.halobridge.<known_block>` is banned

In v2.x, some platform projectors double-emitted compliance blocks
under both the top level AND `extensions.halobridge.<block>`. v3
forbids the latter and the migrator promotes any surviving copies.

### 2. Flat `trust` block

No nested `trust.score.*` / `trust.decision.*` — consumer queries no
longer need to know which key the data lives under. The validator
rejects nested objects under either key.

### 3. Release-gate-enforced safety

Every release-branch push runs the 12-check release safety gate. The
gate refuses to pass if any example envelope leaks. This makes the
privacy contract a CI invariant, not a code-review checklist.

---

## What about regulated verticals?

GalloDoc is workload-agnostic. The optional blocks that matter most
for regulated verticals:

| Block | Use |
|---|---|
| `consent_ledger` | Subject consent records. |
| `chain_of_custody` | Evidence handling chain. |
| `redaction_manifest` | Redaction policies applied to the envelope. |
| `data_residency` | Residency-bound deployment. |
| `training_permissions` | Training consent. |
| `model_risk` | Model risk classification. |
| `retention_status` | Retention policy. |
| `attestations` | Attestation records. |
| `human_decisions` | Reviewer decisions. |
| `evidence_quality` | Evidence scoring. |

All ten are optional in v3.0 — you populate them only when your domain
requires them. The validator's per-block forbidden-key sets are
applied if and only if the block is present.

---

## NL → query plans are safe-by-construction

The v3 NL→GQL planner (`gallodoc.aibi`) produces `QueryPlan` JSON
objects, never executable SQL. The planner has zero capability to
emit:

- `SELECT`, `INSERT`, `UPDATE`, `DELETE` statements.
- Semicolons or backticks (SQL escape characters).
- SQL-comment markers (`--`, `/* */`).

Every plan is scanned by `assert_plan_is_safe`. The planner refuses to
emit a plan that fails the scan. For cross-tenant queries, the planner
emits `federation_intersection` policy_checks derived from the source
envelope's federation policy — those policy_checks are honored by the
executor (a paid component, not in this repo).

---

## Auditing checklist

A compliance lead reviewing a GalloDoc deployment should confirm:

- [ ] Producers run `validate_envelope` before persisting envelopes
  to long-term storage. Invalid envelopes never enter the audit log.
- [ ] Connector emissions run through
  `assert_no_enterprise_leakage` before being committed.
- [ ] Linker entries are not auto-confirmed by any downstream
  pipeline. Only `apply_relationship_decision` should produce
  `status: "confirmed"` entries.
- [ ] Cross-tenant matches verify the federation policy intersection
  on every call.
- [ ] No model weights are committed to any GalloDoc-related repo.
- [ ] The release safety gate (`make release-gate`) runs in CI on
  every push to the release branch.

---

## Further reading

- Spec: [`docs/specs/gallodoc-core-v3-reference-projector.md`](../specs/gallodoc-core-v3-reference-projector.md).
- Spec: [`docs/specs/gallodoc-core-v3-federation.md`](../specs/gallodoc-core-v3-federation.md).
- Migration: [`docs/migration/v1-to-v3.md`](../migration/v1-to-v3.md).
- Release runbook:
  [`docs/v3-design/RELEASE_RUNBOOK.md`](../../../../docs/v3-design/RELEASE_RUNBOOK.md).
- Decisions:
  [`docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md).
