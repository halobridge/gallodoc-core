# Changelog

All notable changes to the open-source `gallodoc` package are recorded here.
The package follows [Semantic Versioning](https://semver.org/).

## [3.0.1] — 2026-05-17

### Fixed

- README: documentation links now use absolute GitHub URLs so they resolve correctly on PyPI's project page (relative paths only work inside the repo, not on rendered package pages).

## [3.0.0] — 2026-05-17

**`gallodoc 3.0.0` is the v3 envelope reference implementation. Cut from
`release/v3.0.0`. The release safety gate (`make release-gate`) passes
every check.**

GalloDoc Core v3 — Portable Operational Intelligence Document Standard.
Adds `gallodoc-core/v3` envelope alongside the preserved v1; consolidates
trust + relationships + source + lifecycle blocks; introduces optional
`federation` top-level; bans `extensions.halobridge.<known_block>` for
the 13 v1.2–v1.6 compliance blocks + `federation`.

The `make release-gate` script ([`scripts/release_safety_gate.py`](scripts/release_safety_gate.py))
runs 12 invariants + 3 supersession-artifact checks against this
release; it must exit 0 with every check pass before tagging.

### Added

- `gallodoc-core/v3` JSON Schema at
  [`gallodoc/schema/gallodoc-core-v3.schema.json`](gallodoc/schema/gallodoc-core-v3.schema.json),
  shipping alongside the unchanged v1 schema file.
- Dual-validator dispatch in `gallodoc.validation.validate_envelope()`:
  envelopes declaring `schema_version: "gallodoc-core/v1"` route to
  `_validate_v1`; `"gallodoc-core/v3"` routes to `_validate_v3`. Same
  dispatch in `validate_with_jsonschema()`.
- Three additive v3 validator rules: (1) linker-discovered relationships
  pin to `status: "suggested"`; (2) `extensions.halobridge.<known_block>`
  is forbidden for the 13 v1.2–v1.6 compliance block names plus
  `federation` (14 names total); (3) nested `trust.score` or
  `trust.decision` objects are forbidden — the v3 trust block is flat.
- Master spec at
  [`docs/specs/gallodoc-core-v3-master-spec.md`](docs/specs/gallodoc-core-v3-master-spec.md)
  and index doc at
  [`docs/specs/gallodoc-core-master.md`](docs/specs/gallodoc-core-master.md).
- Four reference example envelopes under
  [`examples/v3_0/`](examples/v3_0/): minimal, full v3, v1-legacy (copy of
  `gallodoc_pdf_contract.json`).
- Test surface under [`tests/v3_0/`](tests/v3_0/) covering dispatch,
  rules, structural validity, regression against v1/v1.x/v2.0 examples,
  the consolidated relationships / lifecycle / trust shapes, and the
  three reference examples.

### Changed

- **18 required sections** (was 17 in v1). The single addition is the
  consolidated `trust` block. `policy_governance` and `access_control`
  stay optional in v3.0 per the Q6 verification finding; both are tracked
  against the v3.1 promotion checklist.
- `relationships` is now an **object** containing a `relationships[]`
  array (matching the v2.0 `document_relationships` shape) instead of a
  bare array as in v1. Each entry requires the closed `status` enum
  (`suggested | confirmed | rejected`) and a `discovered_by` string.
- `source` absorbs the v2.0 `connector_lineage` shape as an optional
  `source.connector_lineage` sub-block.
- `lifecycle` absorbs the v2.0
  `workflow_execution.workflow_steps[]` shape as an optional
  `lifecycle.workflow_steps[]` array carrying per-step
  `input_hash` / `output_hash`.
- New optional top-level `federation` block. Key reserved with
  `additionalProperties: true`; the full sub-schema ships in a later
  release (prompt 08).
- `gallodoc.schema.load_schema()` accepts an explicit `version` argument
  and defaults to `"gallodoc-core/v3"`. Pass
  `version="gallodoc-core/v1"` for the legacy schema. The v1 validator
  passes the explicit version internally — no behavior change for v1
  callers.
- `GALLODOC_CORE_VERSION` (in `gallodoc/__init__.py`) bumped to
  `"gallodoc-core/v3"`. Python package `__version__` bumped to `"3.0.0"`.
- `Development Status` classifier in `pyproject.toml` bumped from
  `3 - Alpha` to `4 - Beta`. The Alpha classifier was what made revving
  v1 possible; bumping to Beta is part of the supersession move.

### Migration

- The parallel v1 validator stays for **6 months** beginning 2026-05-16
  (per the recommendation in
  [`docs/v3-design/05_v3_master_spec_outline.md §1`](../../docs/v3-design/05_v3_master_spec_outline.md)
  sub-decision and the absence of any other decision).
- Migration helper `gallodoc.migration.v1_to_v3(envelope)` ships in a
  subsequent release (prompt 02 — reference projector). It maps
  `trust_score.*` and `trust_decision.*` into the flat v3 trust layout,
  promotes the 13 v1.2–v1.6 compliance blocks back to top level, and
  rewrites `relationships` from v1's bare array into the v3 object shape.

### Stability

- Required sections will not be removed or renamed without a v4
  envelope. New optional blocks land additively. v3 is **not** described
  as "frozen" — the `frozen → re-rev` pattern only works once and v3 is
  the second time; calling v3 frozen would erode credibility once real
  consumers exist (see Decision 1 in
  [`docs/v3-design/07_decisions.md`](../../docs/v3-design/07_decisions.md)).

### Supersession of v1

- [`docs/GALLODOC_CORE_V1_FROZEN.md`](docs/GALLODOC_CORE_V1_FROZEN.md)
  carries a "Superseded by v3" preamble that names v3 as the successor
  and declares the 6-month parallel-validation window.
- The v1 schema file stays on disk indefinitely (it's only JSON).
- The original v1 freeze commitment is honored within v1's scope: v1
  envelopes continue to validate under the v1 validator unchanged for
  the duration of the deprecation window.

### Added (Codex 02 — reference projector + migration helper)

- `gallodoc.projection.project_to_open_core(envelope)` — open-source
  reference projector. Ports the platform projector's sanitization
  without platform-specific patterns. Closes the largest open-source
  adoption gap (third-party producers no longer need to re-implement
  projection).
- `gallodoc.projection.migrate_v1_to_v3(envelope)` — one-shot migration
  helper. Three transforms (flat trust per Decision 2, relationship
  status injection per Decision 3, Q5 fix promoting
  `extensions.halobridge.<v1.2–v1.6>` to top level). Idempotent.
- `gallodoc.projection.forbidden.EXTENSIONS_HALOBRIDGE_BANNED` —
  canonical 14-name set used by validator + projector + migrator.
- `gallodoc.projection.safety.assert_no_enterprise_leakage(envelope)` —
  privacy assertion for v3 envelopes. Used by the v3-release.yml CI
  privacy scan and (in prompt 10) by `scripts/release_safety_gate.py`.
- `tests/v3_0/projection/` — happy-path + negative test suite.
- `examples/v3_0/migration/` — four envelopes demonstrating projection
  + migration.

### Added (Codex 03 — open connector SDK)

- `gallodoc.connectors` package with `ConnectorSource`, `ConnectorRecord`, `GalloDocConnector`, `ConnectorRunReceipt` interfaces.
- Five starter connectors: `generic_json`, `csv_row`, `pdf_file_metadata`, `salesforce_account_stub`, `invoice_stub`. Each produces a valid v3 envelope with populated `source.connector_lineage`.
- New CLI subcommand: `gallodoc connector convert --connector <slug> --input <path> --out <path>`.
- Tests in `tests/v3_0/connectors/`. Examples in `examples/v3_0/connectors/`.
- Makes the "5-minute install + first envelope" pitch real: `pip install gallodoc && gallodoc connector convert --connector generic_json --input my.json --out out.gdoc.json` produces a valid v3 envelope in one step.
### Added (Codex 04 — GalloUnit-keyed linker)

- `gallodoc.linking` package with deterministic relationship discovery —
  no ML dependencies. Reads GalloUnit hashes, truth_ledger claim IDs,
  `::semantic_intent` values, and source IDs as signals.
- 8-signal weighted scoring with capped shared-evidence contributions
  (per [`docs/specs/gallodoc-core-v3-linker.md`](docs/specs/gallodoc-core-v3-linker.md) §3).
- `link(source_envelope, candidate_envelopes)` → `LinkerOutput`. Every
  candidate emitted with `status: "suggested"` and
  `discovered_by: "gallodoc-linker/3.0.0"` (Decision 3).
- `write_into_envelope(envelope, output)` — appends linker output to
  `relationships.relationships[]` in place. Idempotent.
- `apply_relationship_decision(envelope, relationship_id, verdict, decided_by, rationale=None)` —
  human-review lifecycle helper. Preserves `discovered_by` audit trail.
  Idempotent.
- Deterministic `relationship_id` =
  `"rel_" + sha256(source::target::type)[:16]` — same inputs produce the
  same ID across runs.
- 8th GalloMarkdown block type `::semantic_intent` (Decision 5). Routes
  to `gallounits.units[].semantic_intent`. Initial vocabulary in
  [`docs/specs/gallodoc-semantic-intent-v3.md`](docs/specs/gallodoc-semantic-intent-v3.md).
- Tests in `tests/v3_0/linking/` covering signal extraction,
  classification, decision lifecycle, examples.
- Examples in `examples/v3_0/linking/` (5 envelopes + walkthrough).

### Added (Codex 05 — GalloUnit embeddings adapter)

- `gallodoc.semantic.embeddings` package with `EmbeddingAdapter` interface, the `EmbeddingRecord` shape, and the closed 6-value `PURPOSE_ENUM`.
- Three starter adapters:
  - `local_stub` (deterministic, no extras required) — the default.
  - `bge_m3` (lazy-imported behind `[semantic]` extra).
  - `sentence_transformers` (lazy-imported behind `[semantic]` extra).
- `apply_embeddings(envelope, adapter, purpose)` attaches embeddings to `gallounits.embeddings[]` — embeddings are a sibling array under `gallounits`, NOT a new top-level block.
- Raw vector floats never ship by default. `--include-vector` flag raises `EnterpriseLeakageError` unless `safety_profile.raw_vectors_stored == true` on the envelope.
- New CLI subcommand: `gallodoc semantic embed <input> --adapter <name> --purpose <enum> --out <output>`.
- New `[semantic]` optional install: `pip install gallodoc[semantic]` for the bge_m3 and sentence_transformers adapters.
- Tests in `tests/v3_0/semantic/embeddings/`. Examples in `examples/v3_0/embeddings/`.
- Core stays lightweight — the open-source package's hard-dependency set is unchanged.

### Added (Codex 06 — embedder training lab)

- `gallodoc.training` package with `TrainingPair` schema, the closed 3-value `LABEL_ENUM`, `extract_pairs_from_envelope(s)`, `generate_hard_negatives`, `split_train_dev_test`, and `assert_pairs_clean`.
- Pair sources:
  - **Positives** (`label: "match"`) — `relationships.relationships[]` entries with `status: "confirmed"` AND a matching `relationship_decisions[]` record. **Includes linker-discovered + human-confirmed entries** (Decision 3) — these are the highest-quality supervision signal.
  - **Negatives** (`label: "non_match"`) — entries with `status: "rejected"` AND a matching decision record.
  - **Uncertain** (`label: "uncertain"`) — entries with `status: "suggested"` (no decision yet).
- Four hard-negative strategies: `same_org_wrong_person`, `same_vendor_wrong_invoice`, `similar_clause_different_obligation`, `same_customer_name_different_domain`. All deterministic.
- Deterministic train/dev/test splitter (`seed=42` default; `pair_id`-based bucket assignment guarantees the same pair always lands in the same split).
- Privacy safety scan via `assert_pairs_clean` — every pair passes through `assert_no_enterprise_leakage` (Codex 02). No skip path; export aborts on leak.
- New CLI: `gallodoc training export-pairs --input <envelope.json> --out <pairs.jsonl> [--seed 42] [--ratios 0.8,0.1,0.1] [--include-hard-negatives]`.
- Tests in `tests/v3_0/training/`. Examples in `examples/v3_0/training/`.

### Added (Codex 07 — trained embedder v1)

- **Training recipe** for `gallodoc-bge-m3-v1` at `scripts/train_gallodoc_embedder.py`. Base model: `BAAI/bge-m3`. Contrastive pair learning. Multi-profile output (6 heads, one per `PURPOSE_ENUM` value).
- **No model weights committed.** The recipe is open-source; the weights live externally (HF Hub, S3, internal registry — see `docs/training/lora_export.md`). A `test_no_weights_in_repo.py` scan is the second-line defense after the CI workflow lint job.
- **`--mode tiny`** for CI: runs on `examples/v3_0/training/` fixtures in seconds, CPU-OK, no GPU. Used by the prompt-10 release demo.
- **Evaluation harness** at `scripts/evaluate_gallodoc_embedder.py`. Produces `eval_report.json` with `recall_at_5`, `precision_at_5`, `mrr`, `false_positive_rate`, `per_relationship_type_accuracy`, `semantic_intent_accuracy`, `human_review_agreement_rate`.
- **Decision 5 filter applied:** training pairs must have a resolved `semantic_intent` on source AND target units to count as positives. Pairs without intent are dropped from the positive set.
- **`GalloDocBgeM3V1EmbeddingAdapter`** (`gallodoc.semantic.embeddings.trained`) — new adapter slug `gallodoc_bge_m3_v1`. Lazy-load. `available()` returns `False` without `GALLODOC_BGE_M3_V1_WEIGHTS` configured. Registered in `EMBEDDING_ADAPTERS` (now four entries: `local_stub`, `bge_m3`, `sentence_transformers`, `gallodoc_bge_m3_v1`).
- **Model card template** at `docs/training/model_card_template.md` with required fields: `intended_use`, `limitations`, `safety_rules`, `training_data_requirements`, `evaluation`.
- **LoRA export docs** at `docs/training/lora_export.md`.
- Tests in `tests/v3_0/training/` and `tests/v3_0/semantic/embeddings/`.
- Examples at `examples/v3_0/training/embedder/`.

### Added (Codex 08 — federation block)

- New optional top-level **`federation`** block in the v3 schema (per Decision 4). NOT under `extensions.halobridge.*` — that pattern is rejected by the validator (Codex 01 Rule 2 + Codex 02's banned set).
- `gallodoc.federation` package with `CrossTenantPolicy`, `intersect` (most-restrictive-wins), `is_cross_tenant_match_permitted`, `apply_federation_policy`, `build_matching_receipts`, and `cross_tenant_link`.
- **Sharing scopes:** `tenant_private` (default), `fingerprint_only`, `semantic_only`, `trusted_exchange`, `disabled`. Listed in restrictiveness order.
- **Most-restrictive intersection:** the two tenants' policies intersect; the more restrictive side wins on scope, AND on bool flags, OR on `requires_review`, set intersection on `permitted_relationship_types`.
- **Signal admissibility matrix:** `fingerprint_only` admits hash-based signals (`shared_text_hash`, `shared_claim_id`, `shared_projection_hash`, `shared_source_record_id`, `shared_relationship_value_hash`); `semantic_only` admits embedding-profile signals (`shared_evidence_ref`, `semantic_intent_match`, `shared_semantic_role`); `trusted_exchange` admits both. Keys reflect the `evidence_type` values that Codex 04's `build_evidence` emits.
- **Validator rules added:**
  - Rule 4: `federation.cross_tenant_policy.sharing_scope` must be in the 5-value enum.
  - Rule 5: `federation.matching_receipts[].raw_data_exposed` must be `false` in v3.0. (Reserved for v4 under more rigorous controls.)
- **Schema tightened:** the previously-loose `federation` sub-schema is replaced with structural constraints — `schema_version` const, sharing_scope + method enums, `matching_receipts[]` required keys + `confidence` range.
- New CLI: `gallodoc federation match --source <file> --targets <file_or_glob> --out <output>`.
- Tests in `tests/v3_0/federation/` (policy, enforce, cross_tenant_link, CLI, examples). Examples in `examples/v3_0/federation/` (tenant_a + tenant_b allowed; tenant_c denied; walkthrough README).

### Added (Codex 09 — NL→GQL planner)

- `gallodoc.aibi` package with the `QueryPlan` data model, 6 safe filter primitives (`eq`, `in_`, `has_token`, `has_relationship`, `time_range`, `confidence_at_least`), 5 query templates (`relationship_query`, `semantic_similarity_query`, `operational_timeline_query`, `evidence_chain_query`, `trust_query`), and a federation-aware policy_check generator.
- **Planner ONLY** — targets the v2.0 `query_access` (GQL) grammar; an executor is out of scope for v3.0.
- **No raw SQL ever.** `assert_plan_is_safe` scans every string in the plan for `SELECT`/`INSERT`/`UPDATE`/`DELETE`/semicolons/backticks/SQL comments and raises `UnsafePlanError` on any match.
- **Decision-aware:** filters reference the flat trust path (Decision 2 — `trust.components`, not `trust.score.components`); relationship filters use the `status` field with `confirmed` as default (Decision 3); cross-tenant queries emit `federation_intersection` policy_checks with scopes derived from the source envelope's federation policy (Decision 4).
- Mandatory policy_checks on every relationship + cross-tenant plan.
- New CLI: `gallodoc aibi plan "<natural language>" [--envelope <path>] [--check-only] [--out <path>]`.
- 5 example walkthroughs in `examples/v3_0/aibi/` covering customer_360, invoice_to_employee, website_claim_to_policy, contract_to_salesforce_account, and a cross-tenant federation query.
- `QueryResultReceipt` scaffold for forward-compatibility with future executors.

## [2.1.0] — 2026-05-05

Python package **2.1.0**. Schema family remains **`gallodoc-core/v1`**
(unchanged on the wire). Adds the **GalloMarkdown (`*.gmd`) authoring
layer** plus **document conversion** (`gallodoc convert`). Every v1.x
and v2.0 envelope that validated under 2.0 still validates here.

### Added

- `gallodoc.markdown` — `.gmd` parser (`parse_gallomd`,
  `gallomd_to_gallodoc`, `validate_gallomd`). Seven block types:
  `::gallodoc`, `::artifact`, `::evidence`, `::trust`, `::decision`,
  `::policy`, `::agent_security`.
- `gallodoc.markdown_renderer` — `.gmd` renderer
  (`gallodoc_to_gallomd`, `render_gallodoc_summary`,
  `render_gallodoc_section`). Round-trips with parser. Raw prompts,
  secrets, PHI patterns, and private keys are redacted with a
  `::warning type=safety_redaction` block.
- CLI subcommands: `gallodoc md compile/render/validate/inspect/roundtrip`.
- `gallodoc.conversion` — `convert_file_to_gallomd` with stdlib-only
  readers for `.txt`/`.md`/`.gmd`/`.json`/`.csv`/`.html`/`.xml`/`.eml`,
  plus optional `.pdf` (`gallodoc[pdf]`), `.docx` (`gallodoc[docx]`),
  `.xlsx` (via `openpyxl`).
- CLI subcommand: `gallodoc convert`.
- Multi-file `gallodoc validate` — pass multiple paths or a glob;
  exit non-zero on any failure.
- Examples under `examples/conversion/` and `examples/markdown/`.

### Changed

- Python `__version__` bumped to `2.1.0`. Classifier stays
  `Development Status :: 3 - Alpha`.

See [`RELEASE_NOTES_2.1.0.md`](RELEASE_NOTES_2.1.0.md) for the full
list and the GalloMarkdown spec at
[`docs/specs/gallomarkdown-v1.md`](docs/specs/gallomarkdown-v1.md).

## [2.0.0] — 2026-05-02

Python package **2.0.0**. Schema family remains **`gallodoc-core/v1`**
(unchanged on the wire). Introduces **11 optional, additive top-level
platform blocks**. Older consumers ignore unknown keys.

### Added

- New optional top-level blocks (all `gallodoc.<name>.v2.0`):
  - `query_access` — saved queries, query receipts, query permissions
    (GalloDoc Query Language / GQL).
  - `vector_context` — native RAG: embedding indexes, embedding
    chunks, retrieval receipts.
  - `document_relationships` — first-class cross-document edges,
    evidence, decisions.
  - `temporal_versions` — versioning + replay (versions, change
    events, replay receipts).
  - `policy_governance` — portable policy/rule layer (OPA/Rego-
    compatible): sets, rules, evaluations.
  - `access_control` — roles, permissions, masking rules, access
    receipts.
  - `human_review` — HIM-C-style queues, actions, outcomes.
  - `workflow_execution` — pipelines + steps + artifacts as a
    projection of lifecycle/app runs.
  - `connector_lineage` — connector sources, sync runs, record
    receipts.
  - `compute_trace` — unified spans/metrics/logs (OpenTelemetry-
    compatible at the semantic layer).
  - `artifact_bom` — software/artifact bill-of-materials
    (SPDX/CycloneDX-compatible fields).
- Reference: [`docs/specs/gallodoc-core-v2.0-master-spec.md`](docs/specs/gallodoc-core-v2.0-master-spec.md).
- Examples under `examples/v2_0/`.

### Changed

- Python `__version__` bumped to `2.0.0`. Classifier stays
  `Development Status :: 3 - Alpha` (the on-the-wire envelope identifier
  is unchanged).
- Additional per-block forbidden-key sets enforced by the validator —
  v2.0 introduced the access_control / policy_governance / human_review
  privacy contracts now carried forward to v3.

See [`RELEASE_NOTES_2.0.0.md`](RELEASE_NOTES_2.0.0.md) for the full
list and the v2.0 white paper at
[`docs/whitepapers/gallodoc-2.0-trusted-ai-document-standard.md`](docs/whitepapers/gallodoc-2.0-trusted-ai-document-standard.md).

## [1.3.0] — 2026-05-01 (release candidate)

Python package **1.3.0** — GalloDoc Core **v1.3 RC**. Schema family remains **`gallodoc-core/v1`** (frozen base). Adds documented amendments **v1.1–v1.3** (optional blocks), multi-file `gallodoc validate`, expanded examples and specs, and release-notes doc. Classifier stays **Alpha**. See [`RELEASE_NOTES_1.3.0.md`](RELEASE_NOTES_1.3.0.md).

## [0.1.0] — 2026-05-01

Initial public release of GalloDoc Core v1 — **frozen**.

### Added

- `gallodoc-core/v1` JSON Schema with 17 required top-level sections
  (`schema_version`, `identity`, `source`, `purpose`, `lifecycle`, `activity`,
  `relationships`, `evidence`, `validations`, `security`, `exports`,
  `extensions`, `ai_usage`, `gallounits`, `certification`, `gstp`,
  `truth_ledger`).
- Public spec documents: GSTP v1 (`docs/gstp-v1.md`) and GalloUnits v1
  (`docs/gallounits-v1.md`).
- Synthetic example envelopes for PDF, SQL claim, FHIR, image, audio, video,
  website, connector, evidence packet, and a fully certified GSTP reference.
- `gallodoc.validation` — schema loader plus a stdlib-only validator (richer
  validation when the optional `jsonschema` extra is installed).
- `gallodoc.units` — text normalization, deterministic text hashing, unit
  segmentation (`gallounit_v1`), rule-based unit classifier, and model
  projections (char-count estimator + optional `tiktoken`).
- `gallodoc.artifacts` — regex-based extraction of dates, amounts, emails,
  phone numbers, reference IDs, payment terms, and obvious line-item
  candidates.
- `gallodoc.ai_usage` — empty/add/summarize helpers + `estimate_cost` table.
  Hashes only by default; never stores raw prompts/responses.
- `gallodoc.gstp` — canonical-JSON hashing, manifest builder, payload/manifest
  hash verification, and an optional public-key signature check.
- `gallodoc` CLI — `validate`, `inspect`, `units`, `extract`, `gstp verify`.
- Apache 2.0 license, `pyproject.toml`, GitHub Actions CI workflow, full
  test suite under `tests/`.

### Stability

- v1 is **frozen**. See `docs/GALLODOC_CORE_V1_FROZEN.md`. Required sections
  cannot be removed or renamed; field types cannot change; new optional
  sections are allowed but cannot be made required without v2.

### Excluded by design

This package never ships HaloBridge enterprise internals: connectors, model
prompts, trust-score formulas, policy engine, GSTP signing service, Providence
Certifier workflow, OAuth tokens, or vault references. The open-core
projection is the only sanctioned channel into open-source consumers.
