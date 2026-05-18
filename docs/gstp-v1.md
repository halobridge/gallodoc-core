# GSTP v1 — GalloDoc Secure Transport Package

**Status:** open-core spec, frozen with GalloDoc Core v1.

GSTP is the **GalloDoc Secure Transport Package** — a signed, tamper-evident
portable bundle that wraps a certified GalloDoc plus its evidence so a third
party can verify the package offline without contacting HaloBridge.

This document is the **public spec**. The HaloBridge implementation (signing
service, key registry, revocation feed, online verifier) lives behind the
HaloBridge enterprise boundary and is intentionally out of scope here. Anything
in this spec is safe to implement against by an open-core consumer.

## What GSTP is

GSTP wraps a GalloDoc Core v1 envelope plus its supporting evidence into a
single deterministic package that:

1. Carries a stable **package_id**.
2. Captures a **payload_hash** over the canonical JSON payload.
3. Captures a **manifest_hash** over the manifest (which lists every file and
   its hash).
4. Carries a **signature** over the manifest hash, computed with a
   pre-registered signing key.
5. Carries enough verification metadata for a recipient to confirm authenticity
   **offline** (`verification_mode = offline_verifiable`) when the recipient
   has cached the public key, or **online** when they have not.

The portable file format is implementation-defined (see HaloBridge enterprise
docs). The open-core contract is the **JSON manifest** described below.

## When to create one

A GSTP package is created **only** for a GalloDoc whose `certification.status`
is `certified`. Uncertified envelopes never get a GSTP package — this is what
the `certification_type` field guards. System-attested envelopes can be wrapped
in a GSTP package, but they are clearly marked as
`certification_type = system_attested`, not `human_certified`.

## Package structure

```
<package_id>.gstp/
├── manifest.json          # the GSTP manifest (this spec)
├── envelope.json          # the GalloDoc Core v1 envelope
├── evidence/
│   ├── <evidence_id>.json
│   └── ...
└── signatures/
    └── manifest.sig       # detached signature over manifest.json (canonical bytes)
```

The directory layout is illustrative. Implementations may bundle the contents
into a tar/zip archive or a single signed JSON document; the canonical-JSON
manifest is the source of truth.

## Manifest

```jsonc
{
  "package_id": "...",
  "package_type": "gallodoc_secure_transport_package",
  "schema_version": "gstp/v1",
  "status": "created",                        // not_created | created | verified | failed | revoked
  "created_at": "...",
  "envelope_ref": {
    "path": "envelope.json",
    "sha256": "..."                           // canonical JSON sha256 of the GalloDoc envelope
  },
  "evidence_refs": [
    { "id": "...", "path": "evidence/<id>.json", "sha256": "..." }
  ],
  "payload_hash": "sha256:...",               // sha256 of the canonical envelope+evidence concatenation
  "manifest_hash": "sha256:...",              // sha256 of this manifest with signature_id stripped
  "signature_algorithm": "ed25519",
  "signature_id": "...",                      // reference into the signing service; not the raw signature
  "signed_at": "...",
  "signed_by_org": "...",
  "verification_mode": "offline_verifiable",  // offline_verifiable | online_required | not_available
  "contains": ["envelope", "evidence", "signatures"],
  "verification_instructions": [
    "Re-canonicalize manifest.json (RFC 8785 / canonical JSON), strip signature_id, hash with sha256.",
    "Verify the detached signature in signatures/manifest.sig against the manifest_hash using the public key referenced by public_key_reference.",
    "Re-hash envelope.json and each evidence file; compare with the listed sha256s."
  ],
  "public_key_reference": "...",              // public key id; never the raw private key
  "cert_chain_reference": "..."               // optional cert chain id
}
```

## Canonicalization

GSTP uses **canonical JSON** for hashing:

* keys sorted lexicographically,
* no insignificant whitespace,
* numbers in their canonical decimal form,
* UTF-8 encoding.

`payload_hash` and `manifest_hash` are both `sha256` over canonical JSON. The
existing GalloDoc helper `mvp_core.models._canonical_json_sha256` is the
reference implementation HaloBridge uses; any equivalent canonical-JSON hash
is acceptable.

## Signature algorithm

`ed25519` is the v1 default. Other algorithms are allowed in `signature_algorithm`,
but verifiers MUST treat unknown algorithms as `verification_mode = not_available`
unless they have a registered handler. Algorithm bumps land in v2.

## Verification process

1. **Locate the public key** referenced by `public_key_reference`. Public-key
   distribution is out of scope for this spec — implementations can ship a
   trusted-key bundle, fetch from a registry, or rely on a provided cert chain.
2. **Re-hash the manifest** (canonical JSON, with `signature_id` stripped).
   Compare against `manifest_hash`. Mismatch ⇒ verification fails.
3. **Verify the detached signature** in `signatures/manifest.sig` against the
   re-computed manifest hash using the public key.
4. **Re-hash `envelope.json`** and every entry under `evidence/`. Compare each
   against the listed `sha256`. Mismatch ⇒ verification fails.
5. **Cross-check certification.gstp_package_id** in the GalloDoc envelope —
   it must equal `manifest.package_id`.
6. **Check revocation status.** Recipients who can reach the revocation feed
   should refresh it; offline verifiers may use a cached snapshot whose
   freshness fits their policy.

A package whose verification succeeds and whose `certification.status` is
`certified` is considered authoritative for the certifier's documented scope.

## Certification requirements

GSTP itself does not certify anything — it ships a certification that already
exists inside the GalloDoc envelope. To create a GSTP package the envelope must
contain:

* `certification.status = certified` or `pending` (a pending package is allowed
  but verifiers must treat it as not yet authoritative),
* `certification.certified_by` ⇒ identity reference,
* `certification.policy_id` and `certification.policy_version`,
* `certification.evidence_manifest_hash` matching the GSTP `payload_hash`.

## Certifier / Providence Certifier reference

The certifying authority lives in the optional `certifier` block of the
GalloDoc envelope (see [`gallodoc-core-v1.schema.json`](gallodoc-core-v1.schema.json)).
A GSTP package SHOULD include the `certifier` block when one is present, so
recipients can confirm:

* the certifier's `certifier_type` (e.g. `providence_certifier`, `him_c`, `sme`),
* the `certification_authority` (e.g. *Providence*),
* the `certification_level` (e.g. `HIM-C`),
* the certifier's documented `scope` (allowed document types, packet types,
  jurisdictions, regulations, purposes), and
* the `revocation_status` of the certifier credential at signing time.

Credential secrets never appear in a GSTP package. Only `credential_id` and
`credential_hash` are carried.

## Truth Ledger reference

When the GalloDoc envelope carries `truth_ledger.available = true`, the GSTP
package SHOULD include the truth-ledger snapshot identifier (`current_snapshot_id`)
and `latest_event_hash`. Recipients can replay the ledger out-of-band if they
have access to the enterprise ledger store; the GSTP package itself ships
hashes only.

## Offline verification mode

`verification_mode = offline_verifiable` requires:

* a self-contained public-key bundle (or a cached `public_key_reference`),
* an immutable revocation snapshot dated no later than the package's
  `signed_at` plus the policy-defined freshness window.

`verification_mode = online_required` packages defer revocation and key checks
to a live HaloBridge endpoint. `verification_mode = not_available` is reserved
for envelopes that produced a GSTP shell but could not be signed (e.g. signing
failure during transit) and is treated as `status = failed` by recipients.

## Revocation model

A GSTP package can be revoked at three layers:

1. **Certifier revocation** — `certifier.revocation_status = revoked` revokes
   every package that authority signed within the affected scope window.
2. **Certification revocation** — `certification.status = revoked` plus a
   `certification.revocation_reason` revokes the specific GalloDoc certification
   without invalidating the certifier.
3. **GSTP package revocation** — `gstp.status = revoked` revokes a single
   transit package (e.g. it was sent to the wrong recipient) without affecting
   the underlying certification.

Revocation events propagate via the enterprise revocation feed. Open-core
verifiers see them through their cached snapshot or the online endpoint they
chose at install time.

## Public spec vs HaloBridge implementation boundary

| Concern | Open-core spec (this doc) | HaloBridge enterprise |
|---|---|---|
| Manifest shape | yes | — |
| Canonical-JSON hashing rules | yes | — |
| `signature_algorithm = ed25519` default | yes | — |
| Verification procedure (steps 1-6) | yes | — |
| Public key registry implementation | — | yes |
| Private signing key storage and rotation | — | yes |
| Signing service | — | yes |
| Online revocation feed | — | yes |
| HSM / KMS integration | — | yes |
| Audit log of every signature | — | yes |
| Provider-internal failure analytics | — | yes |

The `gstp` block in [`gallodoc-core-v1.schema.json`](gallodoc-core-v1.schema.json)
mirrors the open-core surface of this spec.
