# GalloDoc Human Review — v2.0

**Schema slug:** `gallodoc.human_review.v2.0`
**Top-level key:** `human_review` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#7-human_review)

HIM-C-style human review queues, actions, and outcomes. Captures reviewer
*role* and *action* without leaking reviewer identity or note bodies.
Pairs naturally with v1.2 `human_decisions` (which records the legal
attestation), with `human_review` covering the operational workflow that
produced that decision.

## Shape

```json
{
  "schema_version": "gallodoc.human_review.v2.0",
  "review_queues": [],
  "review_actions": [],
  "review_outcomes": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `ReviewQueue`   | `queue_id`, `queue_name`, `priority`, `owner_role`, `open_count`, `closed_count`. |
| `ReviewAction`  | `review_id`, `subject_ref`, `reviewer_role`, `him_c_certified`, `action` (`approve`/`reject`/`correct`/`escalate`/`request_more_evidence`), `reason_code`, `notes_hash`, `decided_at`, `evidence_refs[]`. |
| `ReviewOutcome` | `outcome_id`, `subject_ref`, `outcome`, `override_flag`, `trust_score_delta`, `policy_evaluation_ref`, `created_at`. |

## Privacy invariants

- Reviewer notes are never stored by default — only `notes_hash` and an
  optional safe summary. Forbidden keys include `raw_notes`, `notes_body`,
  `reviewer_id`, `reviewer_email`, `reviewer_name`, `reviewer_user_id`.
- `him_c_certified` records that the reviewer is HIM-C-certified for the
  action class — not who the reviewer is.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_human_review.json`](../../examples/v2_0/gallodoc_human_review.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
