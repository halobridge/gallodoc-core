# GalloDoc Query Language (GQL) — v2.0

**Schema slug:** `gallodoc.query_access.v2.0`
**Top-level key:** `query_access` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#1-query_access--gallodoc-query-language-gql)

GalloDoc Query Language is a **safe JSON query/access standard**. It records
the *intent* of a query (filters, return-field allow-list, max results,
safe-mode flag) and a *receipt* per execution (who ran it, when, how many
hits, whether redaction was applied, which policy outcome authorized it).

## Shape

```json
{
  "schema_version": "gallodoc.query_access.v2.0",
  "saved_queries": [],
  "query_receipts": [],
  "query_permissions": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `SavedQuery`     | `query_id`, `name`, `purpose`, `query_type` (`document` / `artifact` / `relationship` / `embedding` / `trust` / `policy` / `timeline`), `filters` (structured JSON), `return_fields[]`, `max_results`, `safe_mode`, `created_by_role`, `created_at`. |
| `QueryReceipt`   | `receipt_id`, `query_id`, `executed_by_role`, `executed_at`, `result_count`, `redaction_applied`, `phi_removed`, `policy_outcome_ref`, `result_hash`. |
| `QueryPermission`| `permission_id`, `query_id`, `allowed_roles[]`, `denied_roles[]`, `scope_summary`, `expires_at`. |

## Privacy invariants

- No native-dialect query strings in public projection. Forbidden keys
  include `raw_sql`, `sql_text`, `sql_query`, `raw_query`,
  `raw_dialect_query` (rejected by the validator).
- No PHI in query receipts; use `result_hash` and `redaction_applied`.
- Saved queries with `safe_mode=false` MUST also have a
  `policy_outcome_ref` proving the call was authorized for unredacted
  return.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_query_access.json`](../../examples/v2_0/gallodoc_query_access.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
