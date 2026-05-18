# GalloDoc Core v1 — schema reference

**Status:** frozen at `gallodoc-core/v1`. See
[`GALLODOC_CORE_V1_FROZEN.md`](GALLODOC_CORE_V1_FROZEN.md) for the stability
rules.

The authoritative JSON Schema lives at
[`../gallodoc/schema/gallodoc-core-v1.schema.json`](../gallodoc/schema/gallodoc-core-v1.schema.json)
and is loaded at runtime via `gallodoc.schema.load_schema()`.

## Required top-level sections (17)

| Section | Purpose |
|---|---|
| `schema_version` | Const `gallodoc-core/v1`. Use it as a discriminator. |
| `identity` | Document identity, type, hash. |
| `source` | Origin system, connector slug, sync run id. |
| `purpose` | Workflow intent (`primary_intent`, `workflow_intent`, `app_slug`). |
| `lifecycle` | Stage timeline + provenance chain. |
| `activity` | Public access trail (no IP / session hashes). |
| `relationships` | Document-to-document edges (duplicate_of, prior_version, …). |
| `evidence` | Bounded reference list. |
| `validations` | Contradictions, packet findings, model disagreements. |
| `security` | PHI / encryption posture summary. |
| `exports` | Bounded export descriptors. |
| `extensions` | Vendor extension namespace (`extensions.<vendor>.*`). |
| `ai_usage` | Provider / model / token / cost / latency ledger. Hashes only. |
| `gallounits` | Model-agnostic semantic evidence units. |
| `certification` | Human-only, evidence-backed attestation. References + hashes only. |
| `gstp` | GalloDoc Secure Transport Package references. |
| `truth_ledger` | Immutable claim/event history references. |

## Optional sections

`certifier`, `media`, `connector_source`, `packets`, `contradictions`,
`external_evidence`, `model_verification`, `trust_score`, `policy`,
`review`, `corrections`, `retention`, `lineage`, `metrics`.

Optional sections are **also** frozen — once they appear they cannot be
renamed or retyped without v2.

## Loading + validating

```python
from gallodoc.schema import load_schema, required_top_level_sections, is_frozen
from gallodoc.validation import load_envelope, validate_envelope, validate_with_jsonschema

schema = load_schema()
assert is_frozen()
print(required_top_level_sections())

env = load_envelope("examples/gallodoc_pdf_contract.json")
result = validate_envelope(env)             # stdlib-only validator
result_full = validate_with_jsonschema(env) # optional jsonschema extra

assert result.valid, [(i.path, i.message) for i in result.issues]
```

## The projection contract

`gallodoc-core/v1` envelopes are produced by the
`project_gallodoc_to_open_core(...)` function in HaloBridge. The function:

* preserves every required section,
* fills safe defaults when the source has nothing,
* strips enterprise-only sections (`fhir`, `structured_data`, `entities`,
  `audit`, `app_results`, `replay_summary`),
* strips secrets, signing keys, ip/session hashes, vault refs, raw prompts,
  raw responses, and tenant ids,
* normalizes vendor data into `extensions.<vendor>.*`.

The open-source package is the verifier; HaloBridge is the producer. Open
implementations of the projection are welcome — keep the same invariants.

## Hashes

Every projected envelope ships a `hashes.envelope_sha256` over the
canonical JSON of every section except `hashes` itself. The hash uses RFC
8785-style canonical JSON (sorted keys, no insignificant whitespace, UTF-8).

## Field map

The full field-by-field map (with `core` / `extension` / `enterprise` /
`future_v2` / `exclude` classification) lives in the HaloBridge repo at
`docs/specs/gallodoc-core-v1-field-map.csv`. The schema and example
envelopes here are the contract; the field map is the rationale.

## Backwards compatibility

Within v1:

* New optional sections may be added.
* New optional fields may be added to existing sections.
* New enum values may be added **only** through a v2 bump.
* Removing or renaming any frozen field is a breaking change.

## Examples

Every example under [`../examples/`](../examples/) validates against this
schema. See [`examples.md`](examples.md) for a guided tour.
