# GalloDoc Core v1.2 — Consent, custody, attestation (optional compliance layer)

## Theme

GalloDoc v1.2 answers, in portable JSON:

- **Why was this allowed?** → `consent_ledger`, `human_decisions`
- **Who consented?** → roles and artifact refs only (`consent_ledger`; no raw signatures or personal identifiers)
- **Where did it go?** → `chain_of_custody` (opaque locations + **hashes**; no raw URLs)
- **Who handled it?** → `human_decisions.reviewer_role`, custody `actor_role`
- **Can we attest to trust state?** → `attestations`, `evidence_quality`

All six blocks are **optional** and **additive** to GalloDoc Core v1.

## Blocks

| Key | `schema_version` constant | Payload shape |
|-----|---------------------------|---------------|
| `consent_ledger` | `gallodoc.consent_ledger.v1.2` | `entries[]` |
| `chain_of_custody` | `gallodoc.chain_of_custody.v1.2` | `events[]` |
| `human_decisions` | `gallodoc.human_decisions.v1.2` | `decisions[]` |
| `attestations` | `gallodoc.attestations.v1.2` | `records[]` |
| `redaction_manifest` | `gallodoc.redaction_manifest.v1.2` | `entries[]` |
| `evidence_quality` | `gallodoc.evidence_quality.v1.2` | `summary` object |

Field semantics in HaloBridge map from retention, review queue, exports, external evidence, security posture, and trust scoring — see `mvp_core/services/gallodoc_compliance_v12_blocks.py` in GalloMVP.

## Public-safety rules

Under these blocks the open-core validator rejects:

- Forbidden secret/signature/identifier **keys** (aligned with execution-governance safety lists plus signature-blob style keys).
- **JWT-shaped** strings, **http(s) URLs**, **non-allowlisted email domains**, and **SSN-shaped** literals anywhere in the subtree.

Run `gallodoc validate <file>` before publishing.

## Schema & example

- Structural definitions: `gallodoc/schema/gallodoc-core-v1.schema.json`
- Reference envelope: `examples/v1_2/gallodoc_consent_custody_attestation.json`
