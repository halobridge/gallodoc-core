# GalloDoc Core v1.3 — Residency, training permissions, model risk, retention

This amendment adds **optional** top-level blocks for AI risk and data-governance signaling. They answer, in portable metadata form:

- Where may this data live?
- Can it be used for model training?
- Which models/providers are allowed (as **class** and **hashed** identifiers only)?
- What model risk posture applies?
- What retention / legal-hold constraints apply?

These blocks are **not** a substitute for contracts or jurisdictional legal advice. They are normative **exchange metadata** so downstream systems can enforce policy consistently.

## Blocks

| Key | `schema_version` constant |
|-----|---------------------------|
| `data_residency` | `gallodoc.data_residency.v1.3` |
| `training_permissions` | `gallodoc.training_permissions.v1.3` |
| `model_risk` | `gallodoc.model_risk.v1.3` |
| `retention_status` | `gallodoc.retention_status.v1.3` |

### `data_residency`

- `residency_policy_id` — opaque policy identifier (not a secret URL).
- `allowed_regions` / `denied_regions` — string region tokens (e.g. cloud region codes), not raw addresses.
- `processing_boundary` / `storage_boundary` — human or coded boundary labels.
- `cross_border_transfer_allowed` — boolean.
- `customer_tenant_boundary` — opaque boundary token (never raw tenant credentials).
- `hipaa_boundary` — coded boundary label when applicable.
- `evaluated_at` — ISO-8601 timestamp when this snapshot was produced.

### `training_permissions`

- `allowed` — boolean summary.
- `permission_level` — one of: `denied`, `internal_only`, `anonymized_only`, `customer_approved`.
- `allowed_uses` / `denied_uses` — string codes (not free-text training instructions).
- `anonymization_required` — boolean.
- `source_basis` — reference to policy instrument (e.g. agreement id / clause tag), not full legal text.
- `expires_at` — ISO-8601 or null.
- `reviewed_by_role` / `reviewed_at` — governance review metadata.

### `model_risk`

- `provider_class` — `local` | `internal` | `external` | `customer_provided`.
- `model_name_hash_or_id` — **hash or opaque id only**; never raw vendor model names if policy forbids disclosure (HaloBridge emits hashes).
- `approval_status` — `approved` | `experimental` | `deprecated` | `blocked`.
- `phi_allowed` — whether PHI-class content may be processed under this posture.
- `external_transmission_allowed` — whether off-prem / vendor API transmission is allowed.
- `max_data_mode` — `redacted` | `masked` | `synthetic` | `full_internal`.
- `reviewed_at` — ISO-8601.
- `policy_version` — governance bundle version string.

### `retention_status`

- `retention_type` — coded type string (e.g. `standard`, `compliance`, `legal_hold`, `archive`).
- `retain_until` — ISO-8601 or null.
- `legal_hold` — boolean.
- `archive_status` — coded lifecycle token (e.g. `active`, `archived`).
- `deletion_allowed` — boolean summary compatible with encryption / hold posture.
- `evaluated_at` — ISO-8601.

## Safety contract (normative)

Open-core envelopes carrying these blocks MUST NOT include:

- Raw model **prompts** or **responses**, training **examples**, or weight blobs.
- The following JSON keys anywhere under the four v1.3 blocks (case-insensitive), enforced by the reference validator:  
  `training_payload`, `fine_tune_dataset`, `training_batch`, `model_weights`, `lora_weights`, `adapter_blob`, `gradient_checkpoint`.
- URLs, JWT-shaped strings, disallowed email domains, or SSN-shaped literals inside these blocks (same hygiene as v1.2 compliance blocks).

See `examples/v1_3/gallodoc_residency_training_model_risk.json` for a synthetic envelope that validates against `gallodoc-core-v1.schema.json` and the reference Python validator.
