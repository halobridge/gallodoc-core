# Linker guide

**Audience:** ops engineers running the GalloUnit-keyed linker against
envelope pairs.
**Reading time:** ~6 minutes.
**Companion spec:**
[`docs/specs/gallodoc-core-v3-linker.md`](../specs/gallodoc-core-v3-linker.md).

---

## What the linker does

The deterministic linker reads pairs of `gallodoc-core/v3` envelopes
and proposes relationship edges between them. **No ML dependencies.**
Signals are extracted from:

- GalloUnit text hashes (`gallounits.units[].text_hash`).
- Truth ledger claim IDs (`truth_ledger.claims[].claim_id`).
- `::semantic_intent` values on units
  (`gallounits.units[].semantic_intent`).
- Source record IDs (`source.source_record_id`).
- Connector lineage record receipts.
- Cryptographic projection hashes.
- Semantic role overlap.
- Evidence reference overlap.

Each signal contributes a weighted score; capped shared-evidence
contributions prevent low-signal mass-matches.

---

## The output contract (Decision 3)

Every relationship the linker proposes lands with:

```json
{
  "status": "suggested",
  "discovered_by": "gallodoc-linker/3.0.0",
  "relationship_id": "rel_<deterministic 16-char sha>"
}
```

The v3 validator pins linker entries to `status: "suggested"` (Codex 01
rule 1). Promotion to `"confirmed"` or `"rejected"` happens via
`apply_relationship_decision()` — see "Human review lifecycle" below.

---

## The 5-minute path

```python
import json
from gallodoc.linking import link, write_into_envelope

source = json.load(open("envelope_a.gdoc.json"))
candidates = [
    json.load(open("envelope_b.gdoc.json")),
    json.load(open("envelope_c.gdoc.json")),
]

output = link(source, candidates)
print(f"discovered {len(output.candidates)} suggested relationships")

# Persist into the source envelope.
write_into_envelope(source, output)
json.dump(source, open("envelope_a_linked.gdoc.json", "w"), indent=2)
```

---

## Human review lifecycle

After the linker writes a suggestion, a reviewer accepts or rejects it:

```python
from gallodoc.linking import apply_relationship_decision

apply_relationship_decision(
    envelope=source,
    relationship_id="rel_abc123",
    verdict="confirmed",         # or "rejected"
    decided_by="human_review:ap_lead",
    rationale="invoice line items match employee approver's auth limit",
)
```

What this does:

1. Sets the relationship's `status` to the new value.
2. **Preserves `discovered_by`** as `"gallodoc-linker/3.0.0"` — the
   audit trail shows machine-proposed + human-confirmed.
3. Appends a record to `relationships.relationship_decisions[]`:

```json
{
  "relationship_id": "rel_abc123",
  "verdict": "confirmed",
  "decided_by": "human_review:ap_lead",
  "decided_at": "2026-05-17T12:00:00Z",
  "rationale": "invoice line items match employee approver's auth limit"
}
```

The function is idempotent: re-applying the same verdict is a no-op.

---

## Deterministic relationship IDs

```
relationship_id = "rel_" + sha256(source::target::type)[:16]
```

Same inputs always produce the same ID. This means:

- The linker is safe to re-run on partial inputs.
- Downstream consumers can dedupe by ID.
- A `rejected` decision survives a re-run — the linker writes the same
  ID and the existing decision keeps it filtered.

---

## What feeds into the score

| Signal | Weight | Source |
|---|---|---|
| `shared_text_hash` | 1.0 | Exact GalloUnit text hash match. |
| `shared_claim_id` | 1.0 | Truth ledger claim shared between envelopes. |
| `shared_projection_hash` | 1.0 | Cryptographic projection match. |
| `shared_source_record_id` | 1.0 | Connector emitted from the same upstream record. |
| `shared_relationship_value_hash` | 0.8 | Shared hashed reference value. |
| `semantic_intent_match` | 0.6 | Matching `::semantic_intent` block (Decision 5). |
| `shared_evidence_ref` | 0.3 (capped) | Same evidence URI. |
| `shared_semantic_role` | 0.1 | Same `semantic_role`. |

A relationship is emitted when the cumulative score is ≥ the configured
threshold (default 0.5).

---

## The `::semantic_intent` GalloMarkdown block (Decision 5)

The linker treats a matching `::semantic_intent` value on source +
candidate units as a strong (weight 0.6) discovery signal. Producers
declare intent in GalloMarkdown:

```gmd
::semantic_intent
intent: invoice_to_employee_approver
::end
```

The block routes to the unit's `gallounits.units[].semantic_intent`
field. The published vocabulary lives at
[`docs/specs/gallodoc-semantic-intent-v3.md`](../specs/gallodoc-semantic-intent-v3.md);
it extends additively in minor releases.

---

## Running the linker on a batch

```bash
# A common ops pattern: source envelope vs. a directory of candidates.
for candidate in /var/envelopes/inbox/*.gdoc.json; do
  python -c "
import json
from gallodoc.linking import link, write_into_envelope

source = json.load(open('source.gdoc.json'))
candidates = [json.load(open('$candidate'))]
output = link(source, candidates)
write_into_envelope(source, output)
json.dump(source, open('source.gdoc.json', 'w'), indent=2)
"
done
```

The linker is deterministic, side-effect-free in the score calculation,
and idempotent (rerunning produces the same `relationship_id`s).

---

## What ships with the linker

| File | Role |
|---|---|
| `gallodoc/linking/__init__.py` | Public API (`link`, `write_into_envelope`, `apply_relationship_decision`, `LinkerOutput`). |
| `gallodoc/linking/signals.py` | Signal extraction. |
| `gallodoc/linking/classifier.py` | Score → relationship type. |
| `gallodoc/linking/lifecycle.py` | Decision-application helpers. |
| `tests/v3_0/linking/` | 8-signal test coverage. |
| `examples/v3_0/linking/` | 5 envelopes + walkthrough. |
| `docs/specs/gallodoc-core-v3-linker.md` | The full spec. |

---

## Federation-aware linking

If both envelopes carry `federation.cross_tenant_policy`, the linker
respects the intersection of the two policies. See
[`docs/positioning/privacy-and-governance-guide.md`](privacy-and-governance-guide.md)
and the federation spec
[`docs/specs/gallodoc-core-v3-federation.md`](../specs/gallodoc-core-v3-federation.md).

---

## Further reading

- Spec: [`docs/specs/gallodoc-core-v3-linker.md`](../specs/gallodoc-core-v3-linker.md).
- Vocabulary: [`docs/specs/gallodoc-semantic-intent-v3.md`](../specs/gallodoc-semantic-intent-v3.md).
- Examples: [`examples/v3_0/linking/`](../../examples/v3_0/linking/).
- The training lab consumes the linker's confirmed positives — see
  [`training-guide.md`](training-guide.md).
