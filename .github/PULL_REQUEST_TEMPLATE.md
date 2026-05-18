<!--
Thanks for the contribution.

Before opening this PR, please confirm:

* the safety scanner is clean: `make release-gate           # 12-check v3 release safety gate`
* the test suite passes:        `pytest -q`
* relevant examples still validate: `gallodoc validate examples/<file>.json`

For schema changes, please confirm:

* `gallodoc-core/v1` is **frozen**. This PR is additive (no removed required
  sections, no renames, no enum value removals, no type changes). If it is
  not additive, the change belongs in v2 — please open a discussion first.
-->

## Summary

What does this PR change? One-paragraph plain-English explanation.

## Why

What problem does this solve? Link to an issue if there is one.

## Changes

* [ ] Schema (`gallodoc/schema/`)
* [ ] Validator (`gallodoc/validation/`)
* [ ] Units engine / classifier / projections (`gallodoc/units/`)
* [ ] Artifacts extractor (`gallodoc/artifacts/`)
* [ ] AI usage helpers (`gallodoc/ai_usage/`)
* [ ] GSTP verifier (`gallodoc/gstp/`)
* [ ] CLI (`gallodoc/cli/`)
* [ ] Examples (`examples/`)
* [ ] Docs (`docs/`, `README.md`, `CHANGELOG.md`)
* [ ] Tests (`tests/`)
* [ ] CI (`.github/workflows/`)

## Testing

Commands you ran locally. Paste the relevant output (≤30 lines).

```bash
pytest -q
make release-gate           # 12-check v3 release safety gate
gallodoc validate examples/gallodoc_pdf_contract.json
gallodoc inspect examples/gallodoc_pdf_contract.json --json
python -m build
```

## Compatibility

* Schema impact: none / additive / breaking (must move to v2)
* New optional dependency: none / `gallodoc[<extra>]`
* Effect on the privacy invariants in `docs/privacy-and-safety.md`: none / describe

## Checklist

- [ ] No PHI / PII / real customer or patient names anywhere in this PR.
- [ ] No credentials, signing keys, OAuth tokens, vault refs, or HaloBridge
      enterprise internals.
- [ ] Tests added or updated.
- [ ] Docs updated (`README.md` and `docs/` as needed).
- [ ] `CHANGELOG.md` entry added under "Unreleased".
- [ ] Release safety gate clean (`make release-gate`).
