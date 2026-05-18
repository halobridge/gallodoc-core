# GalloDoc Core v3 — Federation block (Codex 08)

**Status:** Active. Ships in `gallodoc-core` 3.0.0 (Codex 08).
**Schema slug:** `gallodoc.federation.v3.0`
**Decision reference:** [Decision 4 in `docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md) — federation is a first-class top-level optional block. Never split across `access_control` + `policy_governance`. Never buried under `extensions.halobridge.*`.

## 1. Overview

The `federation` block carries **cross-tenant matching policy** and the **matching receipts** produced when the linker proposes a relationship that crosses tenant boundaries. v3 makes federation a first-class top-level block for two reasons:

1. Tenant-level matching is conceptually distinct from per-actor `access_control` and per-policy `policy_governance`. Overloading either creates a dumping ground.
2. The `extensions.halobridge.*` alternative was rejected because that pattern is itself a double-emission bug being fixed in the same v3 release (see [`docs/v3-design/02_gallomvp_divergence.md §5.1`](../../../../docs/v3-design/02_gallomvp_divergence.md)). Burying federation there would entrench the wrong shape just as v3 fixes it, and would signal that federation is HaloBridge-specific — undercutting the open-standard pitch.

The validator's `EXTENSIONS_HALOBRIDGE_BANNED` set ([`gallodoc/projection/forbidden.py`](../../gallodoc/projection/forbidden.py)) already contains `federation`. The v3 validator's Rule 2 ([`gallodoc/validation/__init__.py`](../../gallodoc/validation/__init__.py)) rejects `extensions.halobridge.federation` envelopes the same way it rejects `extensions.halobridge.consent_ledger`.

## 2. Block shape

```jsonc
{
  "federation": {
    "schema_version": "gallodoc.federation.v3.0",
    "tenant_id_hash": "sha256:...",
    "cross_tenant_policy": {
      "allowed": false,
      "sharing_scope": "tenant_private",
      "raw_data_visible": false,
      "fingerprint_sharing_allowed": false,
      "embedding_sharing_allowed": false,
      "requires_review": true,
      "permitted_relationship_types": []
    },
    "outbound_policy": { /* optional sub-block, future-shape */ },
    "inbound_matches": [
      /* optional list of inbound match summaries */
    ],
    "matching_receipts": [
      {
        "matching_id": "match_<deterministic_suffix>",
        "source_profile_ref": "tenant://...",
        "target_profile_ref": "tenant://...",
        "method": "fingerprint_only",
        "confidence": 0.66,
        "policy_outcome_ref": "policy_outcomes[i]",
        "raw_data_exposed": false,
        "created_at": "2026-05-17T00:00:00Z"
      }
    ]
  }
}
```

The block is **optional**. When absent, every envelope behaves as if it carries a default `tenant_private` policy (no cross-tenant matching).

## 3. `cross_tenant_policy` field semantics

| Field | Type | Default (when block present, field omitted) | Meaning |
|---|---|---|---|
| `allowed` | bool | `false` | Top-level kill switch. If `false`, no cross-tenant matching is permitted regardless of other settings. |
| `sharing_scope` | enum | `"tenant_private"` | One of `tenant_private | fingerprint_only | semantic_only | trusted_exchange | disabled`. Closed enum, validator-enforced. |
| `raw_data_visible` | bool | `false` | **Must be `false` in v3.0.** Reserved for v4 (raw cross-tenant data exchange under more rigorous controls). |
| `fingerprint_sharing_allowed` | bool | `false` | If `true`, hash-only signals (text hash, claim id, projection hash, etc.) may contribute to cross-tenant candidates. |
| `embedding_sharing_allowed` | bool | `false` | If `true`, embedding-profile signals may contribute to cross-tenant candidates. |
| `requires_review` | bool | `true` | If `true`, every cross-tenant candidate produced is annotated as requiring human review. |
| `permitted_relationship_types` | list[str] | `[]` | Allowlist of `relationship_type` values that may be produced cross-tenant. Empty list means no type restriction; non-empty list filters candidates. |

The defaults are intentionally restrictive: a producer that adds a `federation` block to its envelope without setting any sub-fields gets `tenant_private` with `requires_review: true` and no relationship-type allowlist — i.e. a safe no-op.

## 4. Sharing scope enum

| Scope | Signals admissible | Notes |
|---|---|---|
| `tenant_private` | none | Default. No cross-tenant matching. Most restrictive after `disabled`. |
| `fingerprint_only` | hash-based only | `text_hash_match`, `claim_id_match`, `projection_hash_match`, `source_record_id_match`, `relationship_evidence_match`. Other signals filtered. |
| `semantic_only` | embedding-profile only | `shared_evidence_ref`, `semantic_intent_match`, `semantic_role_overlap`. Other signals filtered. |
| `trusted_exchange` | all | Both hash-based and embedding-profile signals admissible. `raw_data_exposed` is still forbidden. |
| `disabled` | none | Federation entirely off. Most restrictive. |

Restrictiveness order (most → least): `disabled` > `tenant_private` > `fingerprint_only` > `semantic_only` > `trusted_exchange`.

The exact signal admissibility table that the enforcement layer uses lives in [`gallodoc/federation/enforce.py`](../../gallodoc/federation/enforce.py) as `_SIGNAL_ADMISSIBILITY`.

## 5. Matching receipt shape

`federation.matching_receipts[]` carries one entry per cross-tenant candidate the linker produced under the intersected policy:

| Field | Type | Required | Notes |
|---|---|---|---|
| `matching_id` | str | yes | Deterministic, derived from `(source_relationship_id)` so re-runs produce stable IDs. |
| `source_profile_ref` | str | no | Opaque tenant-A reference (hashed). Form: `tenant://<sha256_hex>`. |
| `target_profile_ref` | str | no | Opaque tenant-B reference (hashed). |
| `method` | enum | yes | `fingerprint_only | semantic_only | trusted_exchange`. Reflects the effective sharing scope after intersection. |
| `confidence` | float | yes | In `[0.0, 1.0]`. Recomputed from admissible-only signals. |
| `policy_outcome_ref` | str | no | Points at the `policy_governance.policy_outcomes[]` entry that authorized the match. Empty string when policy_governance is not populated. |
| `raw_data_exposed` | bool | yes | **MUST be `false` in v3.0.** Validator rule (Rule 5) rejects envelopes with `true`. |
| `created_at` | str | yes | RFC 3339 / ISO 8601 UTC timestamp. |

**Privacy invariant:** matching receipts carry only hashes and refs. No raw values, no PHI, no PII. The `assert_no_enterprise_leakage` scan (Codex 02) MUST pass on every envelope carrying matching receipts.

## 6. Enforcement matrix — most-restrictive-intersection wins

The operational rule set that the linker layer applies, after Codex 04's signal extraction, is the **most-restrictive-intersection-wins** rule, derived from [`docs/architecture/operational_intelligence_visibility_audit.md`](../../../../docs/architecture/operational_intelligence_visibility_audit.md) Q3.

For two envelopes A and B carrying federation policies P_a and P_b, the effective policy P_eff used to decide whether a cross-tenant candidate survives is:

- `allowed`: `P_a.allowed AND P_b.allowed`
- `sharing_scope`: the more restrictive of the two (lower index in the order list above)
- `raw_data_visible`: `P_a.raw_data_visible AND P_b.raw_data_visible`
- `fingerprint_sharing_allowed`: `P_a.fingerprint_sharing_allowed AND P_b.fingerprint_sharing_allowed`
- `embedding_sharing_allowed`: `P_a.embedding_sharing_allowed AND P_b.embedding_sharing_allowed`
- `requires_review`: `P_a.requires_review OR P_b.requires_review` (if either side wants review, the candidate is flagged)
- `permitted_relationship_types`:
  - both empty → result empty (no restriction)
  - one empty + one non-empty → use the non-empty list
  - both non-empty → set intersection

Then the operational rules:

- `P_eff.allowed == false` → no cross-tenant candidate produced
- `P_eff.sharing_scope ∈ {disabled, tenant_private}` → no cross-tenant candidate produced
- Otherwise: filter the candidate's `relationship_evidence[]` to only signals admissible under `P_eff.sharing_scope`. If no admissible signals remain, drop the candidate.
- If `P_eff.permitted_relationship_types` is non-empty and the candidate's `relationship_type` is not in the list, drop the candidate.
- Recompute the candidate's `confidence` from admissible signals only.
- If `P_eff.requires_review == true`, candidates emitted require human review (downstream consumers annotate accordingly).

## 7. Validator rules introduced in Codex 08

Two new rules layer on top of the v3 validator (in addition to the carry-forward of Codex 01 Rule 2 which bans `extensions.halobridge.federation`):

- **Rule 4:** If `federation.cross_tenant_policy.sharing_scope` is present, it must be in the 5-value enum. Unknown values produce a `ValidationIssue` at `federation.cross_tenant_policy.sharing_scope`.
- **Rule 5:** For every entry in `federation.matching_receipts[]`, `raw_data_exposed` MUST be `false` in v3.0. Envelopes with `true` are rejected with an issue at `federation.matching_receipts[i].raw_data_exposed`.

The schema (Codex 08 commit 2) also enforces structurally:
- `schema_version` is `gallodoc.federation.v3.0` when present
- `cross_tenant_policy.sharing_scope` is in the enum
- `matching_receipts[].method` is in `{fingerprint_only, semantic_only, trusted_exchange}`
- `matching_receipts[].confidence` is in `[0, 1]`
- `matching_receipts[]` entries require `matching_id, method, confidence, raw_data_exposed, created_at`

## 8. Privacy invariants

- **No raw values, ever.** Matching receipts carry only hashes and refs.
- `assert_no_enterprise_leakage` (Codex 02) must pass on every committed example.
- `raw_data_exposed: true` is structurally invalid in v3.0 (Rule 5). The field exists only to make the intent explicit and to give the validator something to assert on — it's not a switch that can be flipped on.

## 9. Forward references

- **Codex 10 release gate:** the release-safety job checks that every committed example envelope with a `federation` block has `federation.matching_receipts[].raw_data_exposed == false`.
- **v4 (future):** `raw_data_visible` and `raw_data_exposed` may become controllable under more rigorous controls. v3.0 reserves the fields and pins them to `false`.

## 10. Related code

| File | Role |
|---|---|
| [`gallodoc/federation/__init__.py`](../../gallodoc/federation/__init__.py) | Package surface (`cross_tenant_link`, re-exports) |
| [`gallodoc/federation/policy.py`](../../gallodoc/federation/policy.py) | `CrossTenantPolicy`, `intersect`, `is_cross_tenant_match_permitted` |
| [`gallodoc/federation/enforce.py`](../../gallodoc/federation/enforce.py) | `apply_federation_policy`, `build_matching_receipts`, signal admissibility matrix |
| [`gallodoc/federation/cli.py`](../../gallodoc/federation/cli.py) | `gallodoc federation match` CLI subcommand |
| [`gallodoc/projection/forbidden.py`](../../gallodoc/projection/forbidden.py) | Contains `federation` in `EXTENSIONS_HALOBRIDGE_BANNED` |
| [`gallodoc/validation/__init__.py`](../../gallodoc/validation/__init__.py) | Rules 2 (ban) + 4 (enum) + 5 (raw_data_exposed) |
| [`gallodoc/schema/gallodoc-core-v3.schema.json`](../../gallodoc/schema/gallodoc-core-v3.schema.json) | Federation sub-schema |

## 11. Examples

See [`examples/v3_0/federation/`](../../examples/v3_0/federation/) — three input envelopes (tenant_a, tenant_b, tenant_c) walked through three output cases (a×b allowed, a×c denied, a×[b,c] mixed). The README in that directory narrates the most-restrictive intersection.
