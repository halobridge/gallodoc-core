# GalloDoc Temporal Versions — v2.0

**Schema slug:** `gallodoc.temporal_versions.v2.0`
**Top-level key:** `temporal_versions` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#4-temporal_versions)

Versioning + replay. Records the version timeline of a GalloDoc envelope,
the change events between versions, and replay receipts proving a past
version still produces the same hashed output under its declared
`policy_version`.

## Shape

```json
{
  "schema_version": "gallodoc.temporal_versions.v2.0",
  "versions": [],
  "change_events": [],
  "replay_receipts": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `Version`        | `version_id`, `parent_version_id`, `document_hash`, `gallodoc_hash`, `created_at`, `created_by_role`, `reason_code`, `status` (`draft`/`active`/`superseded`/`archived`). |
| `ChangeEvent`    | `change_id`, `from_version`, `to_version`, `change_type` (`artifact_added`/`artifact_updated`/`decision_changed`/`policy_changed`/`redaction_changed`/`relationship_changed`/`trust_score_changed`), `field_path_hash`, `before_hash`, `after_hash`, `summary`, `changed_at`. |
| `ReplayReceipt`  | `replay_id`, `version_id`, `replayed_at`, `replayed_by_role`, `output_hash`, `policy_version`, `success`. |

## Privacy invariants

- "What changed" is recorded via `field_path_hash`, `before_hash`,
  `after_hash` — never the raw before/after PHI. Forbidden keys include
  `raw_before`, `raw_after`, `before_value`, `after_value`, `raw_diff`,
  `diff_text`.
- Replay receipts prove a version was successfully replayed under the
  policy version active at that time, without re-shipping inputs.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_temporal_versions.json`](../../examples/v2_0/gallodoc_temporal_versions.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
