# Contributing to GalloDoc Core

Thanks for considering a contribution. GalloDoc Core is the open-source
schema, validator, and verification toolkit for AI-ready, traceable
documents. The contribution surface is intentionally small: we want every PR
to be safe to merge against a frozen v1 contract.

## Ground rules

1. **Never include PHI or PII.** Use the synthetic envelopes under
   [`examples/`](examples) as templates. The release safety scanner will
   reject anything that looks like an SSN, MRN, US-style DOB, or non-
   `example.com` email address.
2. **Never include credentials or signing materials.** Private keys, OAuth
   tokens, vendor API keys, vault references, and HaloBridge enterprise
   internals are blocked by the safety scanner. If you need to demonstrate a
   workflow that involves signing, write the demo against synthetic key
   material that is generated on the fly inside the test.
3. **`gallodoc-core/v1` is frozen.** Required top-level sections cannot be
   removed or renamed. Field types cannot change. Enum values cannot be
   removed or repurposed. Anything that requires those changes lands in
   `gallodoc-core/v2`. See [`docs/GALLODOC_CORE_V1_FROZEN.md`](docs/GALLODOC_CORE_V1_FROZEN.md).
4. **Keep dependencies minimal.** Hard dependencies are zero. Optional
   features go behind `pip install gallodoc[<extra>]`.
5. **Be specific in the PR description.** What, why, and how to test —
   ideally with the exact CLI command(s) you ran.

## Development setup

```bash
git clone https://github.com/halobridge/gallodoc.git
cd gallodoc
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev,schema]
```

Run the test suite + release safety gate before opening a PR:

```bash
pytest -q
make release-gate           # 12-check v3 release safety gate (canonical)
gallodoc validate examples/gallodoc_pdf_contract.json
gallodoc inspect examples/gallodoc_pdf_contract.json --json
python -m build
```

CI runs the same commands across Python 3.10, 3.11, and 3.12.

## What kinds of changes we welcome

* **Bug fixes** — please attach a reproducing test.
* **New optional sections** in `gallounits-v1` and `ai-usage-ledger` shapes,
  following the additive-only rules. Every new section must come with: schema
  update, projection update, field-map row(s), example coverage, tests.
* **New rule-based unit classifier patterns** — keep them deterministic and
  language-agnostic.
* **New artifact extractors** — regex-based only. Bigger ML extractors
  belong in HaloBridge or a downstream package.
* **Optional tokenizer plugins** for `gallodoc.units.projections` — register
  via `register_token_estimator(...)`.
* **Documentation polish** in `README.md` and `docs/`.

## What kinds of changes are out of scope

* GSTP **signing** — this package ships verification only.
* Trust score formulas, policy engine internals, certifier workflow engines,
  Truth Ledger write paths.
* Connectors (Salesforce, FHIR servers, EHR systems, …) — they live in
  HaloBridge.
* Provider-specific raw prompt templates — the package never stores them.

## Code style

* Type-hint everything new.
* Prefer dataclasses for structured returns.
* Keep functions pure where possible; the projection contract relies on it.
* Public APIs go through `__init__.py` `__all__` lists.

## Reporting bugs and security issues

* Bugs: open a GitHub issue using the bug-report template.
* Security issues: see [SECURITY.md](SECURITY.md). Email
  `security@halobridge.ai` privately; do **not** open a public issue.

## License

By contributing you agree your contribution is licensed under
[Apache 2.0](LICENSE).
