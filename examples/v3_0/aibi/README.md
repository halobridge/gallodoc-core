# NL → QueryPlan example walkthroughs

Five worked examples for the Codex 09 NL→GQL planner. Each example has
two files (`*_input.txt` + `*_plan.json`) and may include an
`*_envelope.json` if the planner needs envelope context (e.g. for the
cross-tenant federation example).

Run the planner from CLI to regenerate any plan:

```bash
gallodoc aibi plan "$(cat examples/v3_0/aibi/customer_360_input.txt)" \
    --out examples/v3_0/aibi/customer_360_plan.json
```

(`created_at` is non-deterministic — examples ship a fixed sentinel
timestamp; tests compare modulo this field.)

---

## 1. customer_360

- **NL:** `show all documents linked to customer Acme Corp`
- **Plan type:** `relationship_query`
- **Key filters:**
  - `eq` on `relationships.relationships[].target_label = "customer Acme Corp"`
- **Mandatory policy_checks:**
  - `relationship_status` with `status_in: ["confirmed"]` (Decision 3)
- **Required blocks:** `relationships`, `identity`

The classic "show me everything tied to this customer" query. The planner
recognizes `linked to` as the relationship trigger and extracts the
phrase after it as the relationship target.

## 2. invoice_to_employee

- **NL:** `who approves invoices for vendor Acme?`
- **Plan type:** `relationship_query`
- **Key filters:**
  - `eq` on `relationships.relationships[].target_label = "vendor Acme"`
  - `has_relationship` with `relationship_type = "invoice_to_employee_approver"`,
    `min_confidence = 0.6`
- **Mandatory policy_checks:**
  - `relationship_status` with `status_in: ["confirmed"]`
- **Required blocks:** `relationships`, `identity`

The planner sees the word `approves`/`approver` and adds a
`has_relationship` filter anchored to the specific `relationship_type`
defined for invoice approval flows.

## 3. website_claim_to_policy

- **NL:** `trace evidence for the website claim about pricing`
- **Plan type:** `evidence_chain_query`
- **Key filters:** (none — the planner emits a bare evidence-chain plan;
  an executor would expand from the available evidence in the envelope)
- **Mandatory policy_checks:** none (evidence chains are envelope-local)
- **Required blocks:** `evidence`, `truth_ledger`, `trust`

The `evidence_chain_query` template fires on `trace evidence for`. The
plan asks the executor to chase the truth-ledger and evidence blocks
for this envelope; no relationship or cross-tenant policy is involved.

## 4. contract_to_salesforce_account

- **NL:** `find contracts linked to Salesforce account 001A000000XYZ`
- **Plan type:** `relationship_query`
- **Key filters:**
  - `eq` on `relationships.relationships[].target_label = "Salesforce account 001A000000XYZ"`
  - `has_relationship` with `relationship_type = "same_customer"`,
    `min_confidence = 0.6`
- **Mandatory policy_checks:**
  - `relationship_status` with `status_in: ["confirmed"]`
- **Required blocks:** `relationships`, `identity`

The planner recognizes `salesforce account` and adds the `same_customer`
relationship_type filter — that's the v2.0 enum slot for CRM-account
identity linking.

## 5. cross_tenant_invoice (federation)

- **NL:** `find invoices for vendor Acme across tenants`
- **Envelope:** `cross_tenant_invoice_envelope.json` with
  `federation.cross_tenant_policy.sharing_scope = "fingerprint_only"`
- **Plan type:** `relationship_query`
- **Mandatory policy_checks:**
  - `relationship_status` with `status_in: ["confirmed"]`
  - `federation_intersection` with
    `scopes_allowed: ["fingerprint_only", "trusted_exchange"]`
- **Required blocks:** `relationships`, `identity`

The phrase `across tenants` plus the envelope's `sharing_scope` triggers
the `federation_intersection` policy_check. The `scopes_allowed` list is
the set of remote scopes that would still permit matching against a
`fingerprint_only` source (Decision 4 + the scope map in
`gallodoc-core-v3-aibi-planner.md §9`).
