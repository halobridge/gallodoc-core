# GalloDoc Core 0.1.0 — release notes

**Date:** 2026-05-01
**Status:** release candidate / first public release
**Schema:** `gallodoc-core/v1` — **frozen**.

This is the first public release of GalloDoc Core. The package is the
open-source schema, the validator, the GalloUnits engine, the AI usage
ledger, the basic artifact extractor, and the GSTP verification shell.

---

## What's in 0.1.0

### Schema — frozen at `gallodoc-core/v1`

* 17 required top-level sections: `schema_version`, `identity`, `source`,
  `purpose`, `lifecycle`, `activity`, `relationships`, `evidence`,
  `validations`, `security`, `exports`, `extensions`, `ai_usage`,
  `gallounits`, `certification`, `gstp`, `truth_ledger`.
* Optional sections: `certifier`, `media`, `connector_source`, `packets`,
  `contradictions`, `external_evidence`, `model_verification`,
  `trust_score`, `policy`, `review`, `corrections`, `retention`,
  `lineage`, `metrics`.
* Schema declares `"frozen": true`, `"frozen_version": "gallodoc-core/v1"`,
  `"frozen_at": "2026-05-01"`.
* Authoritative version constant: `gallodoc.GALLODOC_CORE_VERSION`.
* Stability rules:
  [`docs/GALLODOC_CORE_V1_FROZEN.md`](docs/GALLODOC_CORE_V1_FROZEN.md).

### GalloDoc Units

* Deterministic `gallounit_v1` segmentation.
* Stable `unit_id`s derived from canonical text-hash fingerprints.
* Unit types: `sentence`, `paragraph`, `section`, `clause`, `table`,
  `cell`, `image_region`, `audio_segment`, `video_segment`, `entity`,
  `custom`.
* Source spans cover text (`page` / `start_char` / `end_char`), audio
  (`start_time_ms` / `end_time_ms`), video (`region` bbox), and image
  regions.
* sha256 `text_hash` per unit; `canonical_text_hash` per document.

### Validator CLI — `gallodoc validate`

* Stdlib-only validator that checks required sections, types, enums, and
  the `schema_version` constant.
* Optional `gallodoc[schema]` extra adds full `jsonschema` validation.
* Exits `0` when valid, `1` on any error.
* `--json` flag emits machine-readable output.

### Inspector CLI — `gallodoc inspect`

* Prints `schema_version`, document id, document type, source, GalloUnit
  count, AI usage totals, certification status, GSTP status, and Truth
  Ledger state.
* `--json` flag returns the same data as a JSON object.

### Basic artifact extraction — `gallodoc extract`

* Regex-based extractor for `date`, `amount`, `email`, `phone`,
  `reference_id`, `heading`, `payment_terms`, `signature_block`,
  `table_row`, `line_item_candidate`.
* Each artifact carries `artifact_id`, `source_unit_id`, `fields`,
  `value_summary`, `confidence`, `method = "regex_v1"`, and a
  `needs_review` flag.
* Conservative by design — no production-grade accuracy claim.

### AI usage ledger

* `empty_ai_usage()`, `add_ai_run(...)`, `summarize_ai_usage(runs)`,
  `estimate_cost(provider, model, input_tokens, output_tokens)`.
* Stores `prompt_hash` / `response_hash` only — raw bodies NEVER leave
  the originating system through this package.
* `stored_prompt` / `stored_response` flags reflect HaloBridge-side
  retention policy.

### Token / model projections

* Default char-count estimator (`ceil(len(text) / 4)`).
* Optional `tiktoken` plugin via `gallodoc[tokenizer]` for exact OpenAI
  tokenization.
* Plugin interface (`register_token_estimator(...)`) for custom providers.
* Each projection records `provider`, `model_family`, `model`,
  `tokenizer`, `token_count`, and a recomputable `projection_hash`.

### GSTP verification shell

* `canonical_json_bytes(obj)` and `sha256_canonical(obj)` — RFC-8785-style
  canonical JSON with sha256 framing.
* `build_manifest(envelope, ...)` assembles a GSTP manifest with
  `payload_hash` and `manifest_hash`.
* `verify_manifest_hash(manifest)` recomputes and compares the manifest
  hash with `signature_id` stripped.
* `verify_payload_hash(package_dir)` re-hashes every file referenced by
  the manifest.
* `verify_gstp_package(path, public_key=None)` is the top-level verifier.
  Optional ed25519 signature check when `cryptography` is installed.

### Synthetic examples

10 example envelopes under `examples/`, all validating against the
schema. Coverage spans PDF contracts, SQL claim rows, FHIR patient
records, image insurance cards, audio call recordings, video procedure
clips, website compliance scans, Salesforce CRM records, audit-evidence
packets, and a fully certified GSTP reference.

### Release safety scanner

`scripts/release_safety_scan.py` blocks credential-shaped values, signing
materials, raw prompt / response references, internal tenant ids, ip /
session hashes, RFC 1918 internal IPs, and PHI-shaped patterns (SSN, MRN,
mm/dd/yyyy DOB, non-`example.com` email). Runs on every CI build.

### Documentation

* [`README.md`](README.md) — quickstart + positioning.
* [`docs/index.md`](docs/index.md) — documentation map.
* [`docs/gallodoc-core-v1.md`](docs/gallodoc-core-v1.md) — schema reference.
* [`docs/gallodoc-units-v1.md`](docs/gallodoc-units-v1.md) — units engine.
* [`docs/ai-usage-ledger.md`](docs/ai-usage-ledger.md) — AI usage helpers.
* [`docs/artifacts.md`](docs/artifacts.md) — artifact extractor.
* [`docs/gstp-v1.md`](docs/gstp-v1.md) — GSTP package and verifier.
* [`docs/open-core-vs-enterprise.md`](docs/open-core-vs-enterprise.md) — boundary.
* [`docs/privacy-and-safety.md`](docs/privacy-and-safety.md) — privacy invariants.
* [`docs/examples.md`](docs/examples.md) — guided tour of every example.

### Tests + CI

* 50+ tests in `tests/` covering validation, units, classifier,
  projections, artifacts, AI usage, GSTP, CLI, and the safety scanner.
* GitHub Actions matrix on Python 3.10 / 3.11 / 3.12 runs install, lint,
  pytest, per-example validation, PHI / sensitive-pattern scan,
  forbidden-keyword scan, and `python -m build`.

---

## What this release intentionally does NOT include

* **GSTP signing engine.** The verification surface is here; the signing
  service, the private-key registry, and HSM/KMS integration stay in the
  HaloBridge enterprise distribution.
* **Trust scoring formulas.** `trust_score` carries the projected
  components; the formulas are enterprise.
* **Policy engine internals.** Decisions surface in `policy`; the
  formulas, rule sources, and shadow/enforce logic are enterprise.
* **Connectors.** Salesforce / FHIR / SharePoint / EHR adapters live in
  HaloBridge.
* **Certifier workflow engine.** Providence / HIM-C onboarding,
  revocation, and issuance run inside the enterprise certification
  service.
* **Raw prompts / responses / tool-call payloads.** Hashes only.
* **Credentials.** No OAuth, no API keys, no vault references.

See [`docs/open-core-vs-enterprise.md`](docs/open-core-vs-enterprise.md)
for the full boundary.

---

## Compatibility

* Python 3.10, 3.11, 3.12.
* Zero hard dependencies. Optional extras: `schema`, `tokenizer`, `nlp`,
  `pdf`, `docx`, `dev`.
* Schema version: `gallodoc-core/v1` (frozen).
* Package version: `0.1.0` (semver within the v1 schema family).

## Upgrade path from pre-release prototypes

There is no upgrade path. 0.1.0 is the first published release. Anyone
running an internal prototype of GalloDoc against an earlier schema slug
should switch to `gallodoc-core/v1` directly.

## Known limitations

* The artifact extractor is regex-based only — see
  [`docs/artifacts.md`](docs/artifacts.md). Production-grade extraction
  belongs downstream.
* The default token estimator is a char-count heuristic. Install
  `gallodoc[tokenizer]` for exact OpenAI tokenization; other providers
  fall back to the char-count estimate.
* GSTP signature verification requires the `cryptography` package and an
  ed25519 public key in PEM form. Without it, payload integrity is
  verified but signature authenticity is not.

## Acknowledgements

GalloDoc Core was extracted from HaloBridge after a multi-amendment
freeze cycle. The schema, the projection function, and the privacy
invariants were stress-tested against a 50+ test suite plus a
hostile-envelope leakage probe before this release was cut.

## Next

* Tag `v0.1.0` once the public mirror is up.
* Reserve `gallodoc` on PyPI; publish via OIDC trusted-publisher.
* Promote the freeze: marketing pages, launch post, and developer
  walkthrough video.
* Track the v2 backlog (lineage emitters, residency hints, native AI
  usage / Truth Ledger models, closed enums for `purpose.primary_intent`).
