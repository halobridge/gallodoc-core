# GalloDoc Core 1.3.0 — release notes (release candidate)

**Date:** 2026-05-01  
**Status:** release candidate (**Development Status :: Alpha** in `pyproject.toml`)  
**Schema:** `gallodoc-core/v1` — **frozen base**; **v1.1–v1.3** are optional additive amendments.

This release candidate bumps the **Python package** to **1.3.0**. It does **not** rename the schema to `v2`. Publishers upload to PyPI **manually**; this document does not imply a package is live on the index until maintainers publish.

---

## Highlights

### v1.1 — Execution governance

- Optional `execution_governance` block (`schema_version`: `gallodoc.execution_governance.v1.1`).
- Capability tokens, MCP / A2A / skill contracts, delegation policies, execution requests and **receipts** (hashes and opaque IDs — not prompt bodies).
- Reference: [`docs/specs/gallodoc-core-v1.1-execution-governance.md`](docs/specs/gallodoc-core-v1.1-execution-governance.md).

### v1.2 — Consent, custody, attestation

- Optional blocks: `consent_ledger`, `chain_of_custody`, `human_decisions`, `attestations`, `redaction_manifest`, `evidence_quality`.
- Compliance-oriented metadata only (roles, reason codes, hashes, synthetic attestations).
- Reference: [`docs/specs/gallodoc-core-v1.2-consent-custody-attestation.md`](docs/specs/gallodoc-core-v1.2-consent-custody-attestation.md).

### v1.3 — Residency, training permission, model risk

- Optional blocks: `data_residency`, `training_permissions`, `model_risk`, `retention_status`.
- Answers “where may data live?”, “training allowed?”, “provider/model posture?”, “retention/hold?” using **safe fields only** (regions, enums, hashed model identifiers).
- Reference validator rejects dangerous subtree keys (enforced alongside v1.2 hygiene).
- Reference: [`docs/specs/gallodoc-core-v1.3-residency-training-model-risk.md`](docs/specs/gallodoc-core-v1.3-residency-training-model-risk.md).

---

## Open-core guarantees (unchanged)

- **No enterprise policy formulas** — no policy expression blobs or vendor rule engines in this package.
- **No raw prompt/response storage** in open-core envelopes; ledger fields use hashes and flags.
- **No PHI examples** — bundled JSON is synthetic; `scripts/release_safety_scan.py` guards common leak shapes.

---

## Backwards compatibility with v1.0

Envelopes that contain **only** the original seventeen required sections (and no amendment blocks) remain **valid**. Amendment blocks are optional; validators apply extra safety scans **only** when those sections are present.

---

## Tooling

- **`gallodoc validate`** accepts **one or more** JSON files so you can run  
  `gallodoc validate examples/v1_1/*.json` (and similarly for `v1_2`, `v1_3`) under a shell that expands globs.
- **`--json`** with multiple inputs returns a JSON **array** of per-file results (`file` plus the usual `valid`, `issues`, …).

---

## Install / build

```bash
pip install -e ".[dev]"   # from package root
python3 -m build          # produces dist/*.whl and dist/*.tar.gz for 1.3.0
```

See also [`CHANGELOG.md`](CHANGELOG.md) and [`README.md`](README.md).
