# GalloDoc Core v3 — NL→GQL Planner (AI/BI Planner)

**Schema slug:** `gallodoc.aibi.planner.v3.0`
**Module:** `gallodoc.aibi`
**Status:** Ships a **planner ONLY** for v3.0. An executor is out of scope.

The planner takes natural-language text plus optional envelope context and
emits a `QueryPlan` object that targets the existing v2.0 `query_access`
(GQL) grammar. The planner is deterministic and template-based; an ML
variant is reserved for a later release (deferred to a future
`gallodoc[aibi-ml]` extra).

---

## 1. query_access audit findings

The v2.0 `query_access` block already exists in this repository:

- **Schema definition (v3 envelope):**
  `gallodoc/schema/gallodoc-core-v3.schema.json` declares
  `query_access` as an optional object with `additionalProperties: true`
  and the description "Optional v2.0 query_access block (saved queries
  / receipts / permissions)."

- **Schema definition (v2.0 spec):**
  `docs/specs/gallodoc-query-language-v2.md` documents the GQL shape —
  `saved_queries[]`, `query_receipts[]`, `query_permissions[]`. Each
  `SavedQuery` has `query_id`, `name`, `purpose`, `query_type` (closed
  v2.0 enum: `document` / `artifact` / `relationship` / `embedding` /
  `trust` / `policy` / `timeline`), `filters` (structured JSON, never
  SQL), `return_fields[]`, `max_results`, `safe_mode`, `created_by_role`,
  `created_at`.

- **Runtime validation:** `gallodoc/validation/__init__.py`,
  `_validate_v20_field_ranges` (lines ~709–723) validates the
  `query_access.saved_queries[]` and `query_access.query_receipts[]`
  shapes — required fields, ISO timestamps, non-negative `max_results`.

- **Runtime executor:** **none.** A grep across `gallodoc/` returns no
  module that executes a saved query against an envelope. The
  open-source repo ships the GQL *contract* (validator + spec) but not
  an executor. This is expected for v3.0; an executor would belong to a
  commercial runtime layer (e.g. HaloBridge).

**What this planner does:** emits `QueryPlan` objects against the
documented v2.0 grammar. Each plan is a structured JSON document an
external executor could consume to run the query.

**What this planner does NOT do:** execute queries, return results, hit
any data store, or invent a new query language. The plan is the
contract; the runtime is paid / out-of-scope.

---

## 2. Public API

```python
from gallodoc.aibi import plan, QueryPlan, validate_plan, UnsafePlanError

p: QueryPlan = plan("show invoices linked to John")
p_dict = p.to_dict()
```

- `plan(nl: str, envelope: dict | None = None) -> QueryPlan`
  — try each of the 5 template matchers in order; return the first
  match; raise `ValueError` if none match.
- Each plan automatically passes through `validate_plan()` before being
  returned. A plan that fails the safety / field-path checks raises
  `UnsafePlanError`.

---

## 3. QueryPlan shape

```json
{
  "plan_id": "plan_<sha256[:16]>",
  "user_intent_summary": "short natural-language paraphrase",
  "safe_query_type": "<enum>",
  "required_blocks": ["relationships", "trust", "gallounits"],
  "filters": [
    {"op": "eq",                  "field": "...",     "value": "..."},
    {"op": "in_",                 "field": "...",     "values": ["..."]},
    {"op": "has_token",           "field": "gallounits.units[].semantic_intent", "value": "..."},
    {"op": "has_relationship",    "relationship_type": "...", "min_confidence": 0.7},
    {"op": "time_range",          "field": "created_at", "from": "...", "to": "..."},
    {"op": "confidence_at_least", "field": "trust.components[].score", "value": 0.7}
  ],
  "policy_checks": [
    {"check": "federation_intersection", "scopes_allowed": ["fingerprint_only", "trusted_exchange"]},
    {"check": "relationship_status",     "status_in": ["confirmed"]}
  ],
  "expected_output_shape": "list[dict]",
  "max_results": 50,
  "created_at": "2026-05-17T00:00:00Z"
}
```

`plan_id` is deterministic — `"plan_" + sha256(user_intent_summary + "::" + safe_query_type)[:16]`.

---

## 4. Closed enum — `safe_query_type` (5 values)

| value | natural-language pattern |
|---|---|
| `relationship_query` | "find documents linked to X via relationships" |
| `semantic_similarity_query` | "find documents semantically near this one" |
| `operational_timeline_query` | "show events for vendor X in May" |
| `evidence_chain_query` | "trace evidence for this trust score" |
| `trust_query` | "show envelopes certified under policy Y" |

Closed. The planner refuses to emit any other value.

---

## 5. Closed enum — `filter.op` (6 safe primitives)

| op | meaning |
|---|---|
| `eq` | equality (`field == value`) |
| `in_` | set membership (`field in [values]`) |
| `has_token` | token/keyword presence on a GalloUnit (`semantic_intent` / `semantic_role`) |
| `has_relationship` | relationship-edge filter, optionally constrained by `relationship_type` + `min_confidence` |
| `time_range` | `from..to` window on an ISO timestamp field |
| `confidence_at_least` | float field >= threshold |

Closed. **No other ops.** The planner refuses to emit anything else;
`Filter.to_dict()` raises `ValueError` if `op` is not in this set.

---

## 6. No raw SQL — invariant

The planner output **never** contains raw SQL. The
`gallodoc.aibi.safe_filters.assert_plan_is_safe(plan)` helper walks
every string value in `plan.to_dict()` and rejects any of:

- SQL keywords: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`,
  `CREATE`, `TRUNCATE`, `UNION` (case-insensitive, word-boundary).
- Semicolons (`;`)
- Backticks (`` ` ``)
- SQL line comments (`--`)
- SQL block comments (`/*`)

A plan that contains any of these patterns anywhere in any string raises
`UnsafePlanError`. Tests scan the output of every shipped template and
fail the build on regression.

---

## 7. Decision-aware field paths

### Decision 2 — flat `trust` block

Filters reference the **flat** trust shape:

- `trust.components` — list of component scores
- `trust.decision_gates` — list of decision gates
- `trust.policy_outcomes` — list of policy outcomes

The planner **rejects** nested `trust.score.*` and `trust.decision.*`
field paths via `validate_decision_2_flat_trust()`.

### Decision 3 — relationship status

Relationship filters use the v3 shape with `status` ∈
{`confirmed`, `rejected`, `suggested`}. By default, every
`relationship_query` plan emits a mandatory policy_check:

```json
{"check": "relationship_status", "status_in": ["confirmed"]}
```

Unless the user explicitly mentions "suggested" or "rejected" in the NL,
in which case the planner emits a deliberate alternate `status_in`.

### Decision 4 — federation intersection

Any query that crosses tenant boundaries must include a
`federation_intersection` policy_check with `scopes_allowed` derived
from the source envelope's `federation.cross_tenant_policy.sharing_scope`
(see §9 below).

A query is treated as cross-tenant if **either**:

1. The NL contains "across tenants", "cross-tenant", or "tenant boundary".
2. The envelope passed to `plan(...)` has a non-empty `federation` block
   AND the envelope's `sharing_scope` is something other than `tenant_private`.

---

## 8. Allowed field-path prefixes

A filter's `field` must start with one of these envelope-block prefixes
(or be one of a handful of bare relationship-entry field names —
`status`, `discovered_by`, `confidence`, `created_at`). Anything else is
rejected by `validate_field_path()`:

```
identity., source., purpose., lifecycle., activity.,
relationships., evidence., validations., security.,
exports., extensions., ai_usage., gallounits., certification.,
gstp., truth_ledger., trust., federation., policy_governance.,
access_control., human_review., workflow_execution.,
vector_context., temporal_versions., compute_trace.,
artifact_bom., query_access.
```

Bare fields permitted on a relationship entry: `status`,
`discovered_by`, `confidence`, `created_at`, `decided_at`.

This anchors every filter to a known envelope block; arbitrary
attacker-supplied field paths are refused.

---

## 9. Federation scope mapping

Given a source envelope with
`federation.cross_tenant_policy.sharing_scope = X`, the planner emits
`federation_intersection.scopes_allowed = ScopesFor(X)`:

| `sharing_scope` of source | `scopes_allowed` emitted |
|---|---|
| `disabled` | `[]` |
| `tenant_private` | `[]` |
| `fingerprint_only` | `["fingerprint_only", "trusted_exchange"]` |
| `semantic_only` | `["semantic_only", "trusted_exchange"]` |
| `trusted_exchange` | `["fingerprint_only", "semantic_only", "trusted_exchange"]` |

The rule: a remote envelope can match the source iff its
`sharing_scope` is in `scopes_allowed`. The actual most-restrictive
intersection is computed at executor time (Decision 4) — the planner
only records the set of scopes that *could* satisfy the source side.

---

## 10. NL → plan template catalog

Five templates ship — one per `safe_query_type`. Each template documents
its trigger NL pattern (phrase list), the plan it emits, and worked
examples.

### 10.1 `relationship_query`

- **Trigger phrases:** "linked to", "related to", "who approves",
  "invoices for", "supports", "duplicate of".
- **Plan shape (sketch):**
  ```json
  {
    "safe_query_type": "relationship_query",
    "required_blocks": ["relationships", "identity"],
    "filters": [
      {"op": "eq", "field": "relationships.relationships[].target_label", "value": "<noun>"}
    ],
    "policy_checks": [
      {"check": "relationship_status", "status_in": ["confirmed"]}
    ],
    "expected_output_shape": "list[dict]",
    "max_results": 50
  }
  ```
- **Worked example:** `"show invoices linked to John"` →
  `relationship_query` with `target_label="John"`.

### 10.2 `semantic_similarity_query`

- **Trigger phrases:** "similar to", "near this", "documents like".
- **Required blocks:** `gallounits`, `vector_context`.
- **Worked example:** `"find documents similar to this contract"` →
  `semantic_similarity_query` with `has_token` filter on
  `gallounits.units[].semantic_intent`.

### 10.3 `operational_timeline_query`

- **Trigger phrases:** "events in <time period>", "decisions in May",
  "what happened to <doc>", "timeline for".
- **Required blocks:** `lifecycle`, `activity`.
- **Worked example:** `"show all decisions for vendor X in May 2026"` →
  `operational_timeline_query` with `time_range` filter on
  `created_at` and `eq` filter for the vendor.

### 10.4 `evidence_chain_query`

- **Trigger phrases:** "trace evidence for", "evidence for trust
  score", "where did <value> come from".
- **Required blocks:** `evidence`, `truth_ledger`, `trust`.
- **Worked example:** `"trace evidence for trust score on doc_001"` →
  `evidence_chain_query` with `eq` filter on `identity.gallodoc_id`.

### 10.5 `trust_query`

- **Trigger phrases:** "certified under <policy>", "trust at least
  <N>", "high-confidence envelopes".
- **Required blocks:** `trust`, `certification`.
- **Worked example:** `"show envelopes certified under policy v2.1"` →
  `trust_query` with `eq` filter on
  `trust.decision_gates[].policy_ref`.

---

## 11. Mandatory policy_checks

The planner inserts policy_checks automatically:

- **Every `relationship_query`** gets a
  `relationship_status` check with `status_in: ["confirmed"]` (Decision
  3) — unless the NL explicitly mentions "suggested" or "rejected", in
  which case the planner emits a deliberate alternate.

- **Every cross-tenant query** (NL keyword or envelope-derived) gets a
  `federation_intersection` check with `scopes_allowed` per §9 above.

---

## 12. CLI

```
gallodoc aibi plan "<natural-language query>" [--envelope <path>] [--check-only] [--out <path>]
```

- `--envelope <path>` — optional. JSON envelope used as planning context
  (e.g. to derive federation scope).
- `--check-only` — validate that the plan *would* be safe, but do not
  write any output file. Exits `0` on safe-and-valid; non-zero
  otherwise. Useful for dry-runs in CI.
- `--out <path>` — write the plan JSON to `path` (otherwise stdout).

---

## 13. `QueryResultReceipt`

Forward-looking scaffold for downstream executors:

```python
from gallodoc.aibi import build_planning_receipt

r = build_planning_receipt(plan)
# r.status == "planned"
# r.executed_at == None
```

The receipt records:

- `receipt_id` (deterministic from `plan_id` + planner version)
- `plan_id`
- `executed_at` (None until a real executor runs the plan)
- `executed_by_role`
- `result_count`
- `status` ∈ {`planned`, `executed_success`, `executed_failed`,
  `policy_blocked`}
- `policy_outcome_ref`
- `created_at`

The planner only ever returns `status == "planned"` receipts. A real
executor (out of scope for v3.0) would mutate the receipt to record
`executed_*` fields and write it back to
`query_access.query_receipts[]`.

---

## 14. Forward references

- An **executor** is **not** in scope for v3.0. The runtime that
  consumes `QueryPlan` objects and produces `QueryResult` objects is the
  paid commercial layer.
- Prompt 10 (release gate) uses the planner on demo NL queries and
  validates the produced plan shape; it does not exercise an executor.
- A future `gallodoc[aibi-ml]` extra would add an LLM-backed fallback
  for NL inputs that none of the deterministic templates match. Closed
  enums on `safe_query_type` and `filter.op` continue to apply.
