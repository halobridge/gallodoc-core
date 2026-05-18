# Open Core vs HaloBridge Enterprise

`gallodoc` is the data contract and the verification surface. HaloBridge
Enterprise is the production pipeline, the certifying authority, and the
operational runtime. They are complementary, not competing.

## Capability matrix

| Capability | Open-source `gallodoc` | HaloBridge Enterprise |
|---|---|---|
| `gallodoc-core/v1` schema | ✅ | ✅ |
| Validator CLI (`gallodoc validate`) | ✅ | ✅ |
| Inspector CLI (`gallodoc inspect`) | ✅ | ✅ |
| GalloUnits engine | ✅ | ✅ |
| Rule-based unit classifier | ✅ | ✅ |
| Token / model projections — char + optional `tiktoken` | ✅ | ✅ + exact provider tokenizers (OpenAI, Anthropic, Google) |
| Basic artifact extraction (regex) | ✅ | ✅ + ML-backed extractors per domain |
| AI usage ledger helpers | ✅ | ✅ + provider-specific cost reconciliation |
| GSTP **verification** (manifest + payload + signature) | ✅ | ✅ |
| Synthetic example envelopes | ✅ | ✅ |
| GSTP **signing** + private-key registry | — | ✅ |
| HSM / KMS integration | — | ✅ |
| Connectors (Salesforce, FHIR, SharePoint, EHR, …) | — | ✅ |
| Advanced extraction pipelines | — | ✅ |
| Trust-score formulas | — | ✅ |
| Policy engine + decision review | — | ✅ |
| Truth Ledger enforcement (write path) | — | ✅ |
| Providence / HIM-C certification workflow | — | ✅ |
| Operations dashboards & review queues | — | ✅ |

## What lives where

### Open core

* The schema (`gallodoc-core/v1`) and its 17 frozen top-level sections.
* The Python validator (stdlib + optional jsonschema).
* The GalloUnits engine, classifier, and per-model token projections.
* The AI usage ledger helpers — hashes only.
* The basic regex artifact extractor.
* The GSTP verification shell — canonical JSON, manifest hash, payload
  hash, optional ed25519 signature check.
* The CLI: `validate`, `inspect`, `units`, `extract`, `gstp verify`.
* All synthetic example envelopes (PDF, SQL, FHIR, image, audio, video,
  website, connector, evidence packet, certified GSTP reference).
* The release safety scanner.

### HaloBridge enterprise (intentionally NOT in this package)

* GSTP **signing**: signing service, private-key registry, HSM/KMS
  integration, signing-time audit log.
* Connectors and adapters with credentials.
* Advanced extraction pipelines (multi-modal, domain-specific models).
* Trust-score formulas.
* Policy engine internals (rules, formulas, shadow/enforce modes).
* Truth Ledger write path and snapshot service.
* Providence / HIM-C certification workflow engine.
* Internal model identifiers (`halobridge_internal`) and provider
  payload analytics.
* Tenant-aware ip / session hashing, vault refs, secret_refs, and OAuth
  integrations.

The open-core projection function in HaloBridge strips every item in the
"enterprise" list before it produces a `gallodoc-core/v1` envelope. The
package's safety scanner enforces the same boundary on every commit.

## Why split it this way

* **The contract belongs to the community.** A frozen schema and a free
  validator make it possible to integrate against GalloDocs without paying
  a vendor.
* **The production runtime belongs to HaloBridge.** Connectors,
  certification workflows, and signing keys carry operational risk and
  legal obligations that don't fit a permissive open-source license.
* **Verification is open; signing is enterprise.** This mirrors how the
  rest of the cryptographic ecosystem already works (anyone can verify a
  Sigstore bundle; only the signer can produce one).

## Migrating workloads from open core to enterprise

There is no migration. The same schema works on both sides. When you
outgrow the open-source extractor, drop in HaloBridge's; the envelope
shape never changes. When you need a signed transport bundle, HaloBridge
signs it; the open-source verifier still validates the result offline.

## Where to go from here

* Build against the open-source package first.
* Talk to HaloBridge once you need signing, connectors, certification, or
  operational tooling.
