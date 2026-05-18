# GalloDoc Connector Lineage — v2.0

**Schema slug:** `gallodoc.connector_lineage.v2.0`
**Top-level key:** `connector_lineage` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#9-connector_lineage)

Connector ingestion as a first-class GalloDoc trust object. Records each
connector source, the sync runs it produced, and a per-record receipt
tying an ingested external row to its `gallodoc_ref` and the policy
evaluation that authorized the ingest.

## Shape

```json
{
  "schema_version": "gallodoc.connector_lineage.v2.0",
  "connector_sources": [],
  "sync_runs": [],
  "record_receipts": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `ConnectorSource` | `connector_slug`, `connector_category`, `auth_type`, `status`, `source_system_hash_or_id`. |
| `SyncRun`         | `sync_run_id`, `connector_slug`, `started_at`, `completed_at`, `status`, `records_seen`, `records_ingested`, `failures`. |
| `RecordReceipt`   | `receipt_id`, `sync_run_id`, `record_hash`, `source_object_type`, `source_record_id_hash`, `gallodoc_ref`, `policy_evaluation_ref`, `created_at`. |

## Privacy invariants

- Source identifiers and external record IDs are referenced by hash.
  Forbidden keys include `raw_url`, `raw_endpoint`, `raw_record`,
  `record_payload`, `credential`, `auth_credential`.
- The block extends — and never replaces — the v1.0 `source` section,
  which remains the authoritative origin for a given envelope.
- No customer record values, no live URLs, no auth material.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_connector_lineage.json`](../../examples/v2_0/gallodoc_connector_lineage.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
