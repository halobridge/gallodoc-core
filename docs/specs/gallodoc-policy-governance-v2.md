# GalloDoc Policy Governance — v2.0

**Schema slug:** `gallodoc.policy_governance.v2.0`
**Top-level key:** `policy_governance` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#5-policy_governance)

Portable, engine-neutral policy/rule layer. Implementations are free to
use [Open Policy Agent (OPA)](https://www.openpolicyagent.org/) and
[Rego](https://www.openpolicyagent.org/docs/policy-language/), CEL, or a
custom JSON rule engine — the open-core envelope only records hashes,
names, condition summaries, and outcomes. No raw policy bodies ship in
public envelopes.

## Shape

```json
{
  "schema_version": "gallodoc.policy_governance.v2.0",
  "policy_sets": [],
  "policy_rules": [],
  "policy_evaluations": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `PolicySet`         | `policy_set_id`, `name`, `version`, `language` (`json_rules`/`rego`/`cel`/`custom`), `policy_hash`, `status` (`active`/`deprecated`). |
| `PolicyRule`        | `rule_id`, `policy_set_id`, `rule_name`, `purpose`, `action` (`allow`/`warn`/`block`/`require_review`), `condition_summary`, `severity`, `rule_hash`. |
| `PolicyEvaluation`  | `evaluation_id`, `policy_set_id`, `subject_ref`, `action`, `decision`, `matched_rule_refs[]`, `blockers[]`, `warnings[]`, `evaluated_at`. |

## Privacy invariants

- Forbidden keys include `raw_policy_body`, `rego_source`,
  `policy_source`, `rule_body`, `raw_rule_body`. The validator rejects
  any of these inside `policy_governance`.
- `policy_hash` proves provenance; `condition_summary` describes intent.
  The actual rule body stays inside the engine.
- v1.5 `decision_gates` may reference `evaluation_id` as their
  authoritative policy outcome.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_policy_governance.json`](../../examples/v2_0/gallodoc_policy_governance.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
