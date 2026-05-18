# GalloDoc Core v1.5 — Trust Decision

**Schema slug:** `gallodoc.trust_decision.v1.5`  
**Top-level key:** `trust_decision` (optional, additive)

## Purpose

GalloDoc 1.5 answers: **“Can this be trusted enough to act on?”**

The block carries:

- **trust_scores** — structured trust snapshots with explainable component summaries (scores + plain-language explanations).
- **decision_gates** — policy evaluations for concrete actions (export, external model calls, etc.).
- **policy_outcomes** — merged policy decisions with matched rules and required actions.
- **action_recommendations** — prioritized remediation or improvement suggestions.
- **decision_receipts** — durable records linking scores, gates, and outcomes to opaque evidence / execution / export refs.

## Rules (open core)

- **No proprietary formulas:** envelopes MUST NOT include numeric weight matrices or internal scoring code. Use opaque `scoring_profile` slugs only.
- **No sensitive payloads:** no raw PHI, prompts, responses, secrets, JWTs, IP hashes, session hashes, or customer internals.
- **Explainability:** component entries SHOULD include human-readable `explanation` strings suitable for auditors.

## Example

See `examples/v1_5/gallodoc_trust_decision.json`.

## Validation

The bundled validator checks:

- `trust_decision.schema_version` equals `gallodoc.trust_decision.v1.5`.
- Trust scores use grades `A|B|C|D|F` and status values `trusted|review_needed|blocked|insufficient_data`.
- Gate decisions use `allow|warn|block|require_review`.
- Forbidden keys and unsafe string shapes under `trust_decision` are rejected (aligned with other compliance blocks).

### Forbidden keys (illustrative)

These JSON keys MUST NOT appear anywhere under `trust_decision` (non-exhaustive; see `gallodoc.validation`): `raw_phi`, `proprietary_weights`, `formula_weights`, `scoring_weight_matrix`, `tenant_internals`, plus every subtree key the validator rejects under execution governance and earlier compliance blocks (see source catalogue).
