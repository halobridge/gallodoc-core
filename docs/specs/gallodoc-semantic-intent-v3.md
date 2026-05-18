# GalloDoc semantic_intent vocabulary (v3.0)

**Status:** Active (v3.0).
**Field:** `gallounits.units[].semantic_intent`.
**Authoring surface:** `::semantic_intent` GalloMarkdown block (Decision 5).
**Consumers:** `gallodoc/linking/` (signal at weight 0.60 + relationship-type
catalog), and the trained embedder in prompt 07 (label space).

## 1. Concept

`semantic_role` describes what a unit IS (an invoice, an approver
signature, a contract clause). `semantic_intent` describes what a
relationship MEANS or PROPOSES (this invoice goes to this approver;
this contract supersedes that one). Intent and role contribute
independently — Decision 5 in
[docs/v3-design/07_decisions.md](../../../../docs/v3-design/07_decisions.md).

A value in this vocabulary attaches to a single unit via the
`::semantic_intent` block. The linker matches values across envelopes
and emits a candidate relationship using the mapping in §3.

## 2. Vocabulary (starter)

The v3.0.0 vocabulary is the following six values. **The vocabulary
extends additively in minor releases** — new entries may be added in
v3.1+ without breaking existing envelopes. Removals require a v4
envelope.

| Value | Meaning |
|---|---|
| `invoice_to_employee_approver` | This invoice (or invoice line) is routed to this employee approver. |
| `contract_supersedes_contract` | This contract supersedes a prior contract (version-of with directionality). |
| `patient_to_consent_record` | This patient record is governed by this consent. |
| `claim_to_supporting_document` | This claim is supported by this document. |
| `case_to_case_continuation` | This case continues a prior case (derived-from with directionality). |
| `attachment_to_parent_document` | This attachment belongs to the named parent document. |

Unknown values authored in `::semantic_intent` blocks raise
`GalloMDError` at parse time, citing the offending line number. Unknown
values that reach the linker (e.g. via direct envelope construction)
default to `relationship_type = "related_to"` with the intent value
carried in `reason_code` so consumers can still see the author's intent.

## 3. Intent → relationship_type mapping

The linker uses this table when a `semantic_intent_match` signal fires.
The emitted `relationships[]` entry carries the listed `relationship_type`
and `reason_code`.

| `semantic_intent` value | `relationship_type` | `reason_code` |
|---|---|---|
| `invoice_to_employee_approver` | `related_to` | `invoice_to_employee_approver` |
| `contract_supersedes_contract` | `supersedes` | `contract_supersedes_contract` |
| `patient_to_consent_record` | `belongs_to` | `patient_to_consent_record` |
| `claim_to_supporting_document` | `supports` | `claim_to_supporting_document` |
| `case_to_case_continuation` | `derived_from` | `case_to_case_continuation` |
| `attachment_to_parent_document` | `belongs_to` | `attachment_to_parent_document` |

The mapping is enforced in `gallodoc/linking/rules.py`
(`SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE`).

## 4. Extension policy

- New values may be added to this vocabulary in any v3.x minor release.
- A new value must come with a row in §3 mapping it to a v2.0
  `relationship_type` enum value plus a `reason_code` (typically the
  value itself).
- Removing or repurposing an existing value requires a v4 envelope.
- The linker tolerates unknown intent values for forward compatibility
  (it falls back to `related_to` with the intent carried in
  `reason_code`); the `::semantic_intent` block does not, to keep
  authoring tight.
