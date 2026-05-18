# Security Policy

GalloDoc Core is the open-source data contract and verification layer for
GalloDocs. It is **not** the HaloBridge enterprise pipeline; it does not ship
signing materials, credentials, or production extractors.

## What this package stores

By design GalloDoc Core stores **hashes and metadata, not secrets**:

* AI usage records carry `prompt_hash` / `response_hash`. Raw prompts and raw
  responses NEVER ship in the open-core projection.
* GSTP packages carry `payload_hash` / `manifest_hash` and a public-key
  reference. Private signing keys NEVER ship in the open-core projection.
* GalloUnits carry `text_hash` and a bounded `content_summary`. Raw unit
  text is not projected to open-core consumers.
* Tokens, secret_refs, vault refs, OAuth credentials, ip/session hashes, and
  internal tenant ids are stripped at the projection boundary.

The full enumeration lives in [`docs/GALLODOC_CORE_V1_FROZEN.md`](docs/GALLODOC_CORE_V1_FROZEN.md).

## Reporting a vulnerability

**Do not open a public GitHub issue for security reports.**

Email the maintainers at **security@halobridge.ai** with:

* a short description of the issue,
* the affected version,
* steps to reproduce (synthetic data only — see below),
* any suggested mitigation.

We will acknowledge within five business days and aim to ship a fix within
30 days for critical issues.

## Do not submit PHI/PII in issues

If you are reporting a bug, **never** paste real Protected Health Information
(PHI) or Personally Identifiable Information (PII) into an issue, pull
request, or email attachment. Use the synthetic envelopes under
[`examples/`](examples) as a starting point. The maintainers will close
issues that contain real PHI/PII and ask you to redact and resubmit.

## What is out of scope (open core)

GSTP **signing** is intentionally out of scope for this package. The
manifest format, the canonical-JSON hashing rules, and the verification
procedure are all here — but the signer is HaloBridge enterprise. If a
private-key handling issue affects only the enterprise signer, please report
it through the HaloBridge support channel rather than this repo.

## What is in scope (open core)

* The schema (`gallodoc-core/v1`) and its frozen contract.
* The validator, units engine, classifier, AI usage helpers, basic artifact
  extractor, and GSTP verifier.
* The CLI (`gallodoc validate`, `inspect`, `units`, `extract`, `gstp verify`).
* All synthetic example envelopes.
* The release safety scanner.

## Supported versions

| Version | Status |
|---|---|
| 0.1.0 | Active — release candidate / first public release |

The `gallodoc-core/v1` schema itself is **frozen** for the lifetime of the v1
schema family. Breaking changes land in v2; v1 stays patchable for security
fixes.

## Disclosure timeline

* Day 0 — report received.
* ≤ 5 business days — acknowledgement.
* ≤ 30 days — coordinated disclosure for critical issues.
* Public advisory and patched release — published together.
