# GalloDoc Access Control — v2.0

**Schema slug:** `gallodoc.access_control.v2.0`
**Top-level key:** `access_control` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#6-access_control)

Roles, permissions, masking rules, and per-event access receipts. Records
who/what/when/why without leaking identity or PHI: open-core uses
`actor_role` only — never user identity.

## Shape

```json
{
  "schema_version": "gallodoc.access_control.v2.0",
  "roles": [],
  "permissions": [],
  "masking_rules": [],
  "access_receipts": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `Role`           | `role_id`, `role_name`, `scope`. |
| `Permission`     | `permission_id`, `role_id`, `action`, `subject_type`, `allowed`, `constraints[]`. |
| `MaskingRule`    | `masking_rule_id`, `field_class`, `policy`, `display_mode` (`hidden`/`masked`/`hashed`/`role_based`), `applies_to_roles[]`. |
| `AccessReceipt`  | `receipt_id`, `actor_role`, `action`, `subject_ref`, `decision` (`allow`/`deny`/`masked`), `policy_evaluation_ref`, `accessed_at`. |

## Privacy invariants

- Never store user identity. Forbidden keys include `user_id`,
  `user_email`, `user_name`, `actor_id`, `actor_email`, `actor_name`
  (validator rejects these).
- Open-core `access_receipts` carry `actor_role` and a
  `policy_evaluation_ref` — never the raw user record.
- Masking rules describe field classes, not field values.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_access_control.json`](../../examples/v2_0/gallodoc_access_control.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
