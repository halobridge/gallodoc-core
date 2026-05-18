# GalloDoc Core 1.5.0 — release notes (release candidate)

**Date:** 2026-05-01  
**Status:** release candidate (**Development Status :: Alpha** in `pyproject.toml`)  
**Schema:** `gallodoc-core/v1` — **frozen base**; **v1.1–v1.5** are optional additive amendments.

This release candidate bumps the **Python package** to **1.5.0**. It does **not** rename the schema to `v2`. Publishers upload to PyPI **manually**; this document does not imply a package is live on the index until maintainers publish.

---

## Highlights

### v1.5 — Trust score, decision gates, and action outcomes

- Optional `trust_decision` block (`schema_version`: `gallodoc.trust_decision.v1.5`).
- **`trust_scores`** — GalloTrustScore-style snapshots with explainable **components** (evidence quality, lifecycle, security, governance, consent/custody, residency/model risk, agent observability, human review), **drivers**, **blockers**, **warnings**, and **`explanation_summary`** — without proprietary weight matrices in open envelopes.
- **`decision_gates`** — action-level evaluations (export, external model calls, publish, etc.) with minimum scores, required components, and **`allow|warn|block|require_review`** outcomes.
- **`policy_outcomes`**, **`action_recommendations`**, **`decision_receipts`** — governed policy merges, remediation hints, and audit-friendly linkage to opaque refs.
- Reference: [`docs/specs/gallodoc-core-v1.5-trust-decision.md`](docs/specs/gallodoc-core-v1.5-trust-decision.md).
- Example: [`examples/v1_5/gallodoc_trust_decision.json`](examples/v1_5/gallodoc_trust_decision.json).

White paper (narrative): [`docs/whitepapers/gallodoc-1.5-measuring-trust-in-ai-decisions.md`](docs/whitepapers/gallodoc-1.5-measuring-trust-in-ai-decisions.md).

---

## Open-core guarantees (extended)

- **No proprietary scoring formulas** in envelopes — use opaque `scoring_profile` identifiers only; numeric blending stays in enterprise implementations.
- **No raw clinical payloads or model transcripts** in examples or accepted subtrees; validators and `scripts/release_safety_scan.py` enforce hygiene.
- **v1.0–v1.4** optional blocks and semantics unchanged.

---

## Backwards compatibility

Envelopes without `trust_decision` behave as in prior package versions. When present, additional validation applies **only** under that subtree.

---

## Tooling

```bash
gallodoc validate examples/v1_5/gallodoc_trust_decision.json
python3 scripts/release_safety_scan.py
python3 -m pytest tests -q
python3 -m build
```

See also [`CHANGELOG.md`](CHANGELOG.md) and [`README.md`](README.md).
