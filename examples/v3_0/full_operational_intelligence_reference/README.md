# Full Operational Intelligence Reference (v3.0)

End-to-end walkthrough demonstrating every Codex 01–09 contribution
working together: a vendor invoice and an employee record run through
the deterministic linker, augmented by embeddings, confirmed via human
review, and queried through the AI/BI NL → QueryPlan planner.

All data is synthetic. `example.com` domains, fake source IDs,
placeholder sha256 hashes.

---

## The six files

| File | Demonstrates |
|---|---|
| `vendor_invoice.gdoc.json` | A v3 envelope with `source.connector_lineage` (Codex 03), GalloUnits including `semantic_intent` (Codex 04 D5), and a `truth_ledger` claim. |
| `employee_record.gdoc.json` | A companion v3 envelope sharing one `text_hash` with `vendor_invoice` — the cryptographic anchor the linker keys on. |
| `linker_output.json` | `LinkerOutput.candidates` from `link(vendor_invoice, [employee_record])`. One candidate with `relationship_type: "related_to"`, `reason_code: "invoice_to_employee_approver"`, `status: "suggested"`, `discovered_by: "gallodoc-linker/3.0.0"`. |
| `linker_output_with_embeddings.json` | Same candidate set, but generated after `apply_embeddings(...)` was called on both envelopes — demonstrates the embedding-augmented signal set is identical in this case because the deterministic linker's primary signal (shared `text_hash`) dominates. |
| `human_review_decision.json` | `vendor_invoice` after `apply_relationship_decision(env, rel_id, "confirmed", "human_review:ap_lead")`. Shows the Decision 3 lifecycle: `discovered_by` preserved, `status` promoted to `confirmed`, a `relationship_decisions[]` record appended. |
| `aibi_query_receipt.json` | A `relationship_query` plan + a planning receipt. NL: `"who approves invoices for vendor X?"`. |

---

## The flow

```
                vendor_invoice.gdoc.json
                          |
                          | (shared text_hash)
                          v
                employee_record.gdoc.json
                          |
                          | link(...)
                          v
                  linker_output.json
                   (status: suggested)
                          |
                          | apply_embeddings -> link(...)
                          v
            linker_output_with_embeddings.json
                          |
                          | write_into_envelope + apply_relationship_decision
                          v
                human_review_decision.json
                   (status: confirmed)
                          |
                          | plan("who approves invoices for vendor X?", envelope)
                          v
                aibi_query_receipt.json
                (plan + planning receipt)
```

---

## Reproducing the demo programmatically

```python
import json
from pathlib import Path

from gallodoc.linking import link, write_into_envelope, apply_relationship_decision
from gallodoc.semantic.embeddings import apply_embeddings, EMBEDDING_ADAPTERS
from gallodoc.aibi import plan, build_planning_receipt
from gallodoc.validation import validate_envelope

# Step 1 — load envelopes
demo = Path("examples/v3_0/full_operational_intelligence_reference")
vendor = json.load((demo / "vendor_invoice.gdoc.json").open())
employee = json.load((demo / "employee_record.gdoc.json").open())

# Step 2 — link
output = link(vendor, [employee])
print(f"linker suggested {len(output.candidates)} relationship(s)")

# Step 3 — embed + link again (signal-set comparison)
adapter = EMBEDDING_ADAPTERS["local_stub"]()
vendor_emb = apply_embeddings(json.loads(json.dumps(vendor)), adapter, purpose="relationship_embedding")
employee_emb = apply_embeddings(json.loads(json.dumps(employee)), adapter, purpose="relationship_embedding")
output_emb = link(vendor_emb, [employee_emb])

# Step 4 — write linker output into the source envelope + apply human decision
linked = json.loads(json.dumps(vendor))
write_into_envelope(linked, output)
rel_id = output.candidates[0].relationship_id
apply_relationship_decision(
    envelope=linked,
    relationship_id=rel_id,
    verdict="confirmed",
    decided_by="human_review:ap_lead",
    rationale="Invoice approver name hash matches employee record cryptographically",
)

# Step 5 — NL → QueryPlan + planning receipt
query_plan = plan("who approves invoices for vendor X?", linked)
receipt = build_planning_receipt(query_plan)
assert validate_envelope(linked).valid
```

---

## What this exercises

| Codex | Contribution | Where you see it |
|---|---|---|
| 01 | v3 envelope shape + validator dispatch | Every JSON file declaring `schema_version: "gallodoc-core/v3"` validates under `validate_envelope`. |
| 02 | Reference projector + privacy assertion | Both envelopes pass `assert_no_enterprise_leakage`. The release safety gate exercises both checks. |
| 03 | Open connector SDK | `source.connector_lineage` populated on both envelopes. |
| 04 | GalloUnit-keyed linker (D3) | `linker_output.json` carries `status: "suggested"` and `discovered_by: "gallodoc-linker/3.0.0"`. `apply_relationship_decision` promotes to `confirmed` while preserving the audit trail. |
| 05 | Embeddings adapter | `linker_output_with_embeddings.json` was generated from envelopes processed by `apply_embeddings` with the `local_stub` adapter. |
| 06 | Training lab | The confirmed relationship in `human_review_decision.json` would be extracted as a positive `TrainingPair` (label `match`) by `gallodoc.training.extract_pairs_from_envelope`. |
| 07 | Trained embedder | The same envelope shape feeds the `gallodoc_bge_m3_v1` adapter when weights are configured. |
| 08 | Federation | Not exercised in this single-tenant demo. See `examples/v3_0/federation/` for the cross-tenant walkthrough. |
| 09 | NL → GQL planner | `aibi_query_receipt.json.plan` is a `relationship_query` plan; the `policy_checks[]` array carries the mandatory `relationship_status: ["confirmed"]` filter (D3 enforcement). |

---

## Note on timestamps

The `created_at`, `decided_at`, and `plan.created_at` / `receipt.created_at`
fields in these fixtures are captured at generation time (the linker,
decision helper, and planner all stamp ISO timestamps). The release
safety gate does not assert on timestamp values; the e2e test in
`tests/v3_0/release/test_end_to_end_demo_validates.py` asserts only on
structural validity of the JSON files.
