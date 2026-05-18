# Federation examples — tenant A × B × C walkthrough

Three synthetic input envelopes and three computed output envelopes that walk through Codex 08's most-restrictive-intersection-wins enforcement. All envelopes are synthetic; no PHI / PII / tenant IDs.

Spec: [`docs/specs/gallodoc-core-v3-federation.md`](../../../docs/specs/gallodoc-core-v3-federation.md).

## Input envelopes

| File | `cross_tenant_policy` | Shares with |
|---|---|---|
| [`tenant_a_envelope.json`](tenant_a_envelope.json) | `allowed=True`, `sharing_scope="fingerprint_only"`, `requires_review=True`, `permitted_relationship_types=["same_customer", "duplicate_of"]`, `fingerprint_sharing_allowed=True`, `embedding_sharing_allowed=False` | B (text_hash on `invoice_total`), C (text_hash on `customer_ref`) |
| [`tenant_b_envelope.json`](tenant_b_envelope.json) | `allowed=True`, `sharing_scope="trusted_exchange"`, `requires_review=False`, `permitted_relationship_types=[]` (no restriction), `fingerprint_sharing_allowed=True`, `embedding_sharing_allowed=True` | A (text_hash on `invoice_total`) |
| [`tenant_c_envelope.json`](tenant_c_envelope.json) | `allowed=False`, `sharing_scope="tenant_private"`, `requires_review=True`, `permitted_relationship_types=[]` | A (text_hash on `customer_ref`) — but tenant_c denies matching |

## Output envelopes

| File | Candidates | Receipts | Effective scope |
|---|---|---|---|
| [`output_a_x_b.json`](output_a_x_b.json) | 1 — `duplicate_of` (from A's allowlist) targeting tenant_b's invoice | 1 | `fingerprint_only` (A's `fingerprint_only` is more restrictive than B's `trusted_exchange`) |
| [`output_a_x_c.json`](output_a_x_c.json) | 0 — tenant_c's `tenant_private` denies | 0 | n/a |
| [`output_a_x_b_c.json`](output_a_x_b_c.json) | 1 — only the tenant_b match survives | 1 | `fingerprint_only` |

## The intersection

`output_a_x_b.json` is the canonical demonstration: tenant_a's `fingerprint_only` policy is the more restrictive of the two scopes, so the effective scope is `fingerprint_only` even though tenant_b would permit `trusted_exchange`. Only hash-based signals are admissible — the candidate's evidence is filtered to just the `shared_text_hash` entry, the receipt's `method` is `"fingerprint_only"`, and `raw_data_exposed` is `false` (Rule 5).

Tenant_a's `permitted_relationship_types` allowlist (`same_customer`, `duplicate_of`) filters out any other relationship-type the linker might have proposed.

## Privacy invariants

- All envelopes are synthetic.
- All `federation.matching_receipts[].raw_data_exposed` values are `false` in v3.0 (Rule 5).
- All hashes are SHA-256 in `sha256:<64 hex>` form; no raw values.

## Regenerating the outputs

```bash
gallodoc federation match \
  --source examples/v3_0/federation/tenant_a_envelope.json \
  --targets 'examples/v3_0/federation/tenant_b_envelope.json' \
  --out /tmp/output_a_x_b.json
```

The committed outputs use a fixed `created_at` timestamp (`2026-05-17T00:00:00Z`) for deterministic diffs. Re-running the CLI yields the same structural result with a live timestamp.
