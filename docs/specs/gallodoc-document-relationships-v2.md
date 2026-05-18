# GalloDoc Document Relationships — v2.0

**Schema slug:** `gallodoc.document_relationships.v2.0`
**Top-level key:** `document_relationships` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#3-document_relationships)

First-class cross-document edges. Records relationships, the evidence that
drove each match, and explicit confirm/reject decisions so duplicate /
same-claim / same-patient / same-customer joins are auditable end-to-end.

## Shape

```json
{
  "schema_version": "gallodoc.document_relationships.v2.0",
  "relationships": [],
  "relationship_evidence": [],
  "relationship_decisions": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `Relationship`         | `relationship_id`, `source_document_ref`, `target_document_ref`, `relationship_type`, `confidence` (0–1), `status` (`suggested`/`confirmed`/`rejected`), `discovered_by`, `created_at`. |
| `RelationshipEvidence` | `evidence_id`, `relationship_id`, `evidence_type` (`shared_identifier`/`semantic_similarity`/`exact_hash`/`human_review`/`external_reference`), `field_name`, `value_hash`, `explanation_summary`. |
| `RelationshipDecision` | `decision_id`, `relationship_id`, `decision`, `decided_by_role`, `decided_at`, `reason_code`. |

`relationship_type` enum:
`duplicate_of` · `version_of` · `supersedes` · `belongs_to` · `supports` ·
`contradicts` · `same_claim` · `same_patient` · `same_customer` ·
`same_contract` · `same_invoice` · `derived_from` · `related_to`.

## Privacy invariants

- PHI values that drove a match are stored as `value_hash` only.
  Forbidden keys include `raw_field_value`, `field_value`, `patient_name`,
  `raw_match_text` (validator rejects these).
- The block extends — and never replaces — the v1.0 `relationships`
  array, which remains the authoritative document-edge primitive.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_document_relationships.json`](../../examples/v2_0/gallodoc_document_relationships.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
