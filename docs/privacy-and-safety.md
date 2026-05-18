# Privacy and safety

GalloDoc Core is designed so that downstream consumers can adopt the schema
without inheriting the originating system's privacy obligations. This page
enumerates the invariants the open-source package enforces and documents
the categories of data it never carries.

## What an open-core envelope NEVER contains

* Raw prompts. The `ai_usage.runs[]` entries store `prompt_hash` only.
* Raw responses. The `ai_usage.runs[]` entries store `response_hash` only.
* Provider raw HTTP bodies, tool-call payloads, or tool outputs.
* Private signing keys, raw signatures, signing-time secrets, PEM bodies.
* OAuth tokens, API keys, refresh tokens, bearer tokens.
* Vault references (e.g. `secret_ref`) or credential references in resolvable
  form. Only opaque IDs and sha256 credential hashes are projected.
* IP hashes, session hashes, browser fingerprints.
* Tenant identifiers (`tenant_id`) — these belong to the originating
  system, not to a public envelope.
* Raw policy formulas or rule sources. The `policy` section, when present,
  carries decisions only.
* Raw prior-claim values inside the Truth Ledger. Only summaries and
  hashes survive.

## What an open-core envelope CAN contain

* Bounded `content_summary` strings on GalloUnits (≤512 chars). These must
  be PHI-redacted at the originating system before they enter the
  envelope. The schema does not enforce that — the producer does.
* Hashes (`text_hash`, `prompt_hash`, `response_hash`, `payload_hash`,
  `manifest_hash`, `credential_hash`).
* Counts and aggregates (`total_runs`, `total_tokens`, `claim_count`).
* Identifier references (`unit_id`, `run_id`, `package_id`, `signature_id`,
  `public_key_reference`).
* Status enums and timestamps (ISO 8601).
* Vendor extensions under `extensions.<vendor>.*` — vendors must keep
  their own subschemas backwards-compatible AND must NOT reintroduce
  any of the forbidden categories above.

## Producer responsibilities

When a HaloBridge runtime (or any other producer) writes a GalloDoc:

1. Run text and metadata through your PHI / PII detection BEFORE writing
   it into a `content_summary`.
2. Use `data_mode = redacted` (or `masked` / `synthetic`) for any AI run
   whose input was not raw internal text.
3. Ensure the `signature_id`, `public_key_reference`, and
   `credential_hash` fields are opaque references — never the raw key
   material.
4. Store private keys, raw responses, raw prompts, and tenant-aware
   identifiers behind your enterprise boundary, never in the projected
   envelope.

## Consumer guarantees

If you receive a `gallodoc-core/v1` envelope through the open-core
projection (or through GSTP), you can rely on:

* `schema_version == "gallodoc-core/v1"`.
* All 17 required top-level sections present.
* No keys matching the forbidden patterns enforced by the projection
  function (`signing_key`, `private_pem`, `raw_signature`,
  `secret_ref`, etc.).
* No `audit`, `app_results`, `replay_summary`, `fhir`, `structured_data`,
  or `entities` top-level keys (those are enterprise-only).
* `gstp.signature_algorithm == "ed25519"` by default; unknown algorithms
  must be treated as `verification_mode = not_available`.

The release safety gate (`scripts/release_safety_gate.py`, invoked
via `make release-gate`) is the mechanism that enforces these rules
on every push to the release branch. It runs the 12 invariants
documented in `docs/v3-design/RELEASE_RUNBOOK.md §4` plus the three
Decision 1 supersession-artifact checks. The earlier v2.x
`scripts/release_safety_scan.py` was superseded in v3.0.0.

## Examples

All examples under [`../examples/`](../examples/) are **synthetic**:

* No real patient names, real organizations, or real SSNs.
* No mm/dd/yyyy DOBs (the safety scanner blocks that pattern).
* All emails use the `example.com` domain.
* All hashes are illustrative.
* All organization identifiers (e.g. "Synthetic Providence Authority") are
  marked as synthetic.

## Reporting privacy concerns

If you believe a published envelope or document contains PHI / PII,
credentials, or any other protected data, email
`security@halobridge.ai` privately. Do **not** open a public issue.
See [`../SECURITY.md`](../SECURITY.md).
