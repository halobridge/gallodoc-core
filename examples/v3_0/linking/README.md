# GalloDoc v3 linker — worked example

Five files demonstrating the deterministic linker end-to-end:

| File | Role |
|---|---|
| [`source_envelope.json`](source_envelope.json) | Synthetic vendor-invoice envelope (source). Carries `gallounits.units[]` with `text_hash`, an `evidence_ref`, a `source_record_id_hash`, and a unit marked with `semantic_intent: "invoice_to_employee_approver"`. |
| [`candidate_envelope.json`](candidate_envelope.json) | Synthetic employee-record envelope. Shares one `text_hash` with the source, one `evidence_ref`, the same `semantic_intent`, and the same `semantic_role` (`approver_ref`) — fires four signals. |
| [`linker_output.json`](linker_output.json) | The `LinkerOutput.candidates[]` produced by `link(source, [candidate])`. One candidate with `relationship_type: "related_to"`, `reason_code: "invoice_to_employee_approver"`, confidence 1.0 (the four signal weights sum past 1.0 and clamp). |
| [`source_with_relationship.json`](source_with_relationship.json) | The source envelope after `write_into_envelope`. Demonstrates the in-place append into `relationships.relationships[]` with `status: "suggested"` and `discovered_by: "gallodoc-linker/3.0.0"`. |
| [`source_confirmed.json`](source_confirmed.json) | The previous file after `apply_relationship_decision(env, rel_id, "confirmed", "human_review", rationale="vendor verified")`. The entry's `status` flips to `confirmed`, `discovered_by` is preserved (the audit trail shows machine-proposed + human-confirmed), and a record is appended to `relationships.relationship_decisions[]`. |

## How to reproduce

```python
from gallodoc.linking import (
    apply_relationship_decision, link, write_into_envelope,
)

source = json.loads(open("source_envelope.json").read())
candidate = json.loads(open("candidate_envelope.json").read())

# 1. Run the linker
out = link(source, [candidate])
# out.candidates has one entry — see linker_output.json

# 2. Merge into the source envelope
write_into_envelope(source, out)
# source.relationships.relationships[] now has the entry — see source_with_relationship.json

# 3. Human review confirms the entry
rel_id = out.candidates[0].relationship_id
apply_relationship_decision(source, rel_id, "confirmed", "human_review", rationale="vendor verified")
# source.relationships.relationship_decisions[] now has the record — see source_confirmed.json
```

## What this demonstrates

- **Decision 3** — every linker-emitted entry carries
  `status: "suggested"` and `discovered_by: "gallodoc-linker/3.0.0"`.
  `apply_relationship_decision` preserves `discovered_by` and appends to
  `relationship_decisions[]`.
- **Decision 5** — the matched `semantic_intent` value lands in
  `reason_code` (and on the candidate's `semantic_intent` field) and
  flows through the relationship-type catalog. Intent overrides the
  signal-pattern path.
- **Determinism** — running `link()` twice produces the same
  `relationship_id`. The example fixture's value
  (`rel_b1a6ffa24c474dc4`) is `"rel_" + sha256("doc_invoice_001::doc_employee_001::related_to")[:16]`.
- **Privacy invariants** — all locators are opaque field-path strings;
  all values are hashes or short vocabulary tokens; no raw text or PHI
  appears in linker output.

## Note on synthetic data

All identifiers, hashes, and source systems are synthetic. The example
uses `example.com/ap` and `example.com/hr` as system identifiers and
hex-repeated `sha256:aaaa…` / `sha256:bbbb…` placeholders for content
hashes. Do not treat any value here as production input.
