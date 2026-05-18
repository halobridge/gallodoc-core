# GalloDoc Core v3 — GalloUnit-keyed deterministic linker

**Status:** Active (v3.0).
**Slug:** `gallodoc.linking.v3.0`
**Module:** [`gallodoc/linking/`](../../gallodoc/linking/)
**Locked decisions:** Anchors 3 and 5 in [docs/v3-design/07_decisions.md](../../../../docs/v3-design/07_decisions.md).

## 1. Overview

The linker is a deterministic relationship-discovery component for v3
envelopes. It reads cryptographic anchors (`gallounits.units[].text_hash`,
`gallounits.model_projections[].projection_hash`,
`truth_ledger.claims[].claim_id`) plus author-asserted intent
(`gallounits.units[].semantic_intent`) and proposes
`relationships.relationships[]` entries. No machine learning is used —
the linker is hash and ID matching with a transparent weighted sum.

The linker exists in open-source because v3 envelopes are individually
valuable but, on their own, do not answer the practical operator
question "I have envelopes; how do I connect them?" Closing that gap
without forcing every consumer to re-implement deterministic matching is
the linker's reason for being.

## 2. Locked output contract (Decision 3)

Linker output writes into the v3 envelope's `relationships` block. Every
emitted entry pins:

- `status = "suggested"` — the v2.0 closed enum slot. The v3 validator
  (rule 1) rejects any entry whose `discovered_by` matches
  `r"^.*linker.*$"` and whose `status != "suggested"`. The linker cannot
  publish a confirmed relationship.
- `discovered_by = "gallodoc-linker/3.0.0"` — running version pin. The
  audit trail is preserved when human review later flips an entry to
  `confirmed` / `rejected`; `discovered_by` is never overwritten.

The linker **appends** to `relationships.relationships[]`; it never
overwrites the array. Re-running the linker on the same inputs produces
the same `relationship_id` values so consumers can de-dup. Idempotency:
when an entry with the same `relationship_id` already exists, the linker
replaces that entry in place rather than appending a duplicate.

**Determinism.** `relationship_id` is a stable function of
`(source_document_id, target_document_id, relationship_type)`:

```python
relationship_id = "rel_" + sha256(f"{source}::{target}::{type}").hexdigest()[:16]
```

Running the linker twice on the same inputs produces identical
`relationship_id` values.

No parallel `linker_results` staging block ships. The v2.0 `status: suggested`
slot is the canonical staging mechanism — consumers that want
"confirmed only" views filter on `status == "confirmed"`.

## 3. Signal table

The linker scores each (source, candidate) pair against eight signals.
Confidence is the weighted sum of matching signals, clamped to `[0, 1]`.

| Signal | Source | Weight | Notes |
|---|---|---|---|
| Matching `gallounits.units[].text_hash` | source ∩ candidate | 0.95 | Strongest — same canonical unit text. |
| Matching `truth_ledger.claims[].claim_id` | source ∩ candidate | 0.85 | Same canonical claim across documents. |
| Matching `gallounits.model_projections[].projection_hash` | source ∩ candidate | 0.70 | Same tokenization-stable content (same model + same text). |
| Shared `truth_ledger.claims[].evidence_refs` | source ∩ candidate | 0.60 | Per shared ref, capped at 3 contributions. |
| Matching `gallounits.units[].semantic_intent` (Decision 5) | source ∩ candidate | 0.60 | Author-asserted relationship intent. Strong evidence of a proposed relationship, weaker than cryptographic anchors but stronger than role heuristics. |
| Matching `source.source_record_id` (or hash) | source ∩ candidate | 0.50 | Same external system record. |
| Matching `relationships.relationship_evidence[].value_hash` | source ∩ candidate | 0.40 | Pre-existing hashed-value match. |
| Semantic role overlap on `gallounits.units[].semantic_role` | source ∩ candidate | 0.10 | Heuristic tie-breaker only. Role describes what a unit IS; intent describes what a relationship MEANS — independent. |

**Confidence formula.** `confidence = min(1.0, sum_of_matching_signal_weights)`.
The shared evidence refs signal contributes at most `SHARED_EVIDENCE_REF_CAP = 3`
times so one envelope cannot dominate via many shared refs. No ML.

Weights are tuning constants in `gallodoc/linking/scoring.py` (`SIGNAL_WEIGHTS`).
The v3.0.0 weights are recommendations; an empirical validation pass
against labelled corpora is planned for v3.1.

## 4. Relationship-type catalog

The linker emits values from the v2.0 `document_relationships.relationship_type`
enum verbatim. The full set (matches `_validate_v20_field_ranges` in
[`gallodoc/validation/__init__.py`](../../gallodoc/validation/__init__.py)):

```
duplicate_of, version_of, supersedes, belongs_to, supports,
contradicts, same_claim, same_patient, same_customer,
same_contract, same_invoice, derived_from, related_to
```

The linker maps signal combinations to types by priority. A higher-priority
match wins:

| Priority | Signal | Emitted relationship_type | reason_code |
|---|---|---|---|
| 1 | `semantic_intent_match` | per intent mapping below | the intent value |
| 2 | `claim_id_match` | `same_claim` | `shared_canonical_claim` |
| 3 | `text_hash_match` | `duplicate_of` | `shared_canonical_text` |
| 4 | `source_record_id_match` | `duplicate_of` | `shared_source_record_id` |
| 5 | `projection_hash_match` | `derived_from` | `shared_tokenization_stable_content` |
| 6 | (default) | `related_to` | `null` |

`semantic_intent` overrides the signal-pattern mapping when present
(Decision 5). The intent-to-relationship-type table lives in
`gallodoc/linking/rules.py` (`SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE`) and
matches the starter vocabulary in
[`gallodoc-semantic-intent-v3.md`](gallodoc-semantic-intent-v3.md):

| `semantic_intent` value | Emitted relationship_type | reason_code |
|---|---|---|
| `invoice_to_employee_approver` | `related_to` | `invoice_to_employee_approver` |
| `contract_supersedes_contract` | `supersedes` | `contract_supersedes_contract` |
| `patient_to_consent_record` | `belongs_to` | `patient_to_consent_record` |
| `claim_to_supporting_document` | `supports` | `claim_to_supporting_document` |
| `case_to_case_continuation` | `derived_from` | `case_to_case_continuation` |
| `attachment_to_parent_document` | `belongs_to` | `attachment_to_parent_document` |

Unknown `semantic_intent` values default to `related_to` with the intent
value carried in `reason_code` — the vocabulary extends additively
across minor releases, so unknown intents are tolerated rather than
rejected at the linker level. (The `::semantic_intent` GalloMarkdown
block, by contrast, rejects unknown vocabulary at parse time — see §6.)

## 5. `::semantic_intent` integration (Decision 5)

GalloMarkdown gains an 8th block type, `::semantic_intent`, that resolves
to `gallounits.units[].semantic_intent`. Authoring surface:

```
::semantic_intent
unit_id: gu_017
intent: invoice_to_employee_approver
::
```

The block attaches an intent value to a specific unit. The linker reads
matching intent values across envelopes as a signal at weight 0.60, and
the relationship-type catalog (§4) consults the matched intent first.

Vocabulary is documented in
[`gallodoc-semantic-intent-v3.md`](gallodoc-semantic-intent-v3.md). The
vocabulary extends additively in minor releases. The
`::semantic_intent` block rejects unknown values at parse time with
`GalloMDError`.

## 6. `apply_relationship_decision` (Decision 3 lifecycle)

```python
apply_relationship_decision(
    envelope: dict,
    relationship_id: str,
    verdict: Literal["confirmed", "rejected"],
    decided_by: str,
    rationale: str | None = None,
) -> dict
```

The canonical (and only) supported path to flip a linker-suggested entry.
Behavior:

- Finds the relationship by `relationship_id`. Raises `ValueError` if not
  found.
- Sets `status` to `confirmed` or `rejected`. Raises `ValueError` on any
  other `verdict`.
- Preserves `discovered_by` — the audit trail shows the link was
  machine-proposed AND human-confirmed.
- Appends a record to `relationships.relationship_decisions[]` with
  `decision_id`, `relationship_id`, `verdict`, `decided_by`, `decided_at`,
  `rationale`.
- Idempotent: re-applying the same verdict on an already-decided entry
  is a no-op (no duplicate decision record).

A v3.1 follow-up may add a state-transition validator that disallows
`status: "rejected"` entries from being silently re-promoted to
`suggested` without a corresponding decision record — out of scope for
v3.0.

## 7. Privacy invariants

The linker reads **only** hashes, IDs, and short vocabulary strings. No
raw text, no PHI, no credentials. The emitted `relationships[]` entries
and `relationship_evidence[]` records carry only:

- IDs (e.g. `claim_id`, `gallodoc_id`, `relationship_id`, `evidence_id`)
- Hashes (`text_hash`, `projection_hash`, `value_hash`, `source_record_id_hash`)
- Opaque locator strings of the form `gallounits.units[unit_id=u1].text_hash`
- Vocabulary tokens (`semantic_intent`, `semantic_role`, `evidence_type`)
- Numeric weights / confidence scores

Tests assert no raw text or PHI-like patterns survive into linker output.

## 8. Test surface

`tests/v3_0/linking/` covers:

- Signal extraction — each of the 8 signals independently.
- Confidence formula — single signal, multi-signal stacking, clamping at
  1.0, shared-evidence cap at 3.
- Relationship-type catalog — each priority rule, every documented
  `semantic_intent` mapping, unknown intent fallback.
- `apply_relationship_decision` lifecycle — confirmed / rejected /
  invalid verdict / missing relationship / idempotency.
- Output validation — every linker-emitted relationship pins to
  `status: "suggested"` and `discovered_by: "gallodoc-linker/3.0.0"`,
  and the resulting envelope passes `validate_envelope`.
- Determinism — re-running the linker produces the same
  `relationship_id` values.
- GalloMarkdown grammar — `::semantic_intent` block parses, routes, and
  round-trips; unknown vocabulary raises `GalloMDError`.

## 9. Forward references

- **Prompt 06 (Embedder Training Lab):** linker-confirmed positives feed
  the training set. Pairs filter on `status == "confirmed"` (linker
  output) plus `status == "confirmed"` (human-curated relationships) —
  same filter.
- **Prompt 07 (Trained Embedder v1):** the model reads
  `gallounits.units[].semantic_intent` values as relationship-target
  labels. `semantic_intent_accuracy` joins `relationship_type_accuracy`
  on the model card.

## 10. Out of scope (v3.0)

- Tuning signal weights against labelled corpora — planned for v3.1.
- Promotion of `semantic_intent` from `reason_code` to a first-class
  relationship field — deferred until intent corpora exist and read
  patterns are clearer.
- State-transition validation (e.g. preventing silent
  `rejected → suggested` re-promotions) — flagged for v3.1.
- Performance bounds beyond a soft benchmark — the linker is O(N×M) by
  design; a hard performance gate ships with v3.1 once a baseline exists.
