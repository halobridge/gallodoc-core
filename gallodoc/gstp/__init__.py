"""GalloDoc Secure Transport Package — open-core verification shell.

This module ships **verification only**. Private signing materials and the
HaloBridge enterprise signing service are not included.

Functions:

* :func:`canonical_json_bytes` — RFC-8785-style canonical JSON.
* :func:`sha256_canonical` — sha256 over ``canonical_json_bytes``.
* :func:`build_manifest` — assemble a GSTP manifest dict for an envelope plus
  optional evidence file references.
* :func:`verify_manifest_hash` — recompute and compare the manifest hash.
* :func:`verify_payload_hash` — re-hash files referenced by a manifest.
* :func:`verify_gstp_package` — top-level verifier; accepts a directory layout
  or a standalone manifest path.

Optional signature verification — when a public key is supplied — uses
``ed25519`` if `cryptography` is installed; otherwise it returns a warning
and skips the signature check.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Canonical JSON
# ---------------------------------------------------------------------------


def canonical_json_bytes(obj: Any) -> bytes:
    """Return canonical JSON bytes of ``obj`` (sorted keys, no whitespace)."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_canonical(obj: Any) -> str:
    """sha256 of ``canonical_json_bytes(obj)``, prefixed ``sha256:``."""
    return f"sha256:{hashlib.sha256(canonical_json_bytes(obj)).hexdigest()}"


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# Build manifest
# ---------------------------------------------------------------------------


def build_manifest(
    envelope: dict[str, Any],
    *,
    evidence_refs: list[dict[str, Any]] | None = None,
    package_id: str | None = None,
    signed_by_org: str = "",
    signature_algorithm: str = "ed25519",
    public_key_reference: str = "",
    cert_chain_reference: str = "",
    verification_mode: str = "offline_verifiable",
) -> dict[str, Any]:
    """Build a GSTP manifest dict for the given envelope.

    The returned manifest carries a ``payload_hash`` over the canonical
    envelope+evidence concatenation and a ``manifest_hash`` over a normalized
    copy of itself with the signature id stripped, so verifiers can recompute
    both deterministically.
    """
    payload_obj = {
        "envelope": envelope,
        "evidence": evidence_refs or [],
    }
    payload_hash = sha256_canonical(payload_obj)

    manifest: dict[str, Any] = {
        "package_id": package_id or sha256_canonical(envelope.get("identity") or envelope),
        "package_type": "gallodoc_secure_transport_package",
        "schema_version": "gstp/v1",
        "status": "created",
        "envelope_ref": {"path": "envelope.json", "sha256": sha256_canonical(envelope)},
        "evidence_refs": list(evidence_refs or []),
        "payload_hash": payload_hash,
        "manifest_hash": "",
        "signature_algorithm": signature_algorithm,
        "signature_id": "",
        "signed_at": "",
        "signed_by_org": signed_by_org,
        "verification_mode": verification_mode,
        "contains": ["envelope", "evidence"],
        "verification_instructions": [
            "Re-canonicalize manifest.json (canonical JSON), strip signature_id, hash with sha256.",
            "Compare against the listed manifest_hash.",
            "Re-hash envelope.json and each evidence file; compare with the listed sha256s.",
        ],
        "public_key_reference": public_key_reference,
        "cert_chain_reference": cert_chain_reference,
    }
    manifest["manifest_hash"] = _compute_manifest_hash(manifest)
    return manifest


def _compute_manifest_hash(manifest: dict[str, Any]) -> str:
    """Recompute ``manifest_hash`` for a manifest with ``signature_id`` stripped."""
    safe = dict(manifest)
    safe["signature_id"] = ""
    safe["manifest_hash"] = ""
    return sha256_canonical(safe)


# ---------------------------------------------------------------------------
# Verification result
# ---------------------------------------------------------------------------


@dataclass
class GstpVerificationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    manifest_hash_ok: bool = False
    payload_hash_ok: bool | None = None
    signature_ok: bool | None = None
    package_id: str = ""
    package_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "package_id": self.package_id,
            "package_type": self.package_type,
            "manifest_hash_ok": self.manifest_hash_ok,
            "payload_hash_ok": self.payload_hash_ok,
            "signature_ok": self.signature_ok,
            "issues": list(self.issues),
            "warnings": list(self.warnings),
        }


# ---------------------------------------------------------------------------
# Verify manifest + payload
# ---------------------------------------------------------------------------


def verify_manifest_hash(manifest: dict[str, Any]) -> bool:
    declared = str(manifest.get("manifest_hash") or "")
    recomputed = _compute_manifest_hash(manifest)
    return declared == recomputed


def verify_payload_hash(package_dir: str | Path) -> tuple[bool, list[str]]:
    """Re-hash files referenced by ``package_dir/manifest.json`` and compare."""
    package_dir = Path(package_dir)
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.is_file():
        return False, [f"missing manifest.json under {package_dir}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    issues: list[str] = []

    env_ref = manifest.get("envelope_ref") or {}
    env_rel = env_ref.get("path")
    env_expected = env_ref.get("sha256") or ""
    if env_rel:
        env_path = package_dir / env_rel
        if not env_path.is_file():
            issues.append(f"envelope file missing: {env_rel}")
        else:
            envelope = json.loads(env_path.read_text(encoding="utf-8"))
            actual = sha256_canonical(envelope)
            if actual != env_expected:
                issues.append(
                    f"envelope sha256 mismatch (expected {env_expected}, got {actual})"
                )

    for ref in manifest.get("evidence_refs") or []:
        rel = ref.get("path")
        expected = ref.get("sha256") or ""
        if not rel:
            continue
        path = package_dir / rel
        if not path.is_file():
            issues.append(f"evidence file missing: {rel}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            issues.append(f"evidence sha256 mismatch for {rel} (expected {expected}, got {actual})")

    return (not issues), issues


# ---------------------------------------------------------------------------
# Optional signature verification
# ---------------------------------------------------------------------------


def _verify_signature(
    manifest_hash: str,
    signature_path: Path,
    public_key_pem: str,
    algorithm: str,
) -> tuple[bool | None, list[str]]:
    """Return ``(ok, warnings)``. ``ok`` is None when verification was skipped."""
    if algorithm and algorithm.lower() != "ed25519":
        return None, [f"unsupported signature_algorithm {algorithm!r} — verification skipped."]
    if not signature_path.is_file():
        return None, [f"signature file missing: {signature_path}"]
    try:
        from cryptography.hazmat.primitives import serialization  # type: ignore  # noqa: PLC0415
        from cryptography.exceptions import InvalidSignature  # type: ignore  # noqa: PLC0415
    except ImportError:
        return None, ["`cryptography` not installed — signature verification skipped. Install with `pip install cryptography` to verify."]
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    except Exception as exc:  # pragma: no cover
        return None, [f"could not load public key: {exc}"]
    sig_bytes = signature_path.read_bytes()
    try:
        public_key.verify(sig_bytes, manifest_hash.encode("utf-8"))
        return True, []
    except InvalidSignature:
        return False, ["signature does not match manifest hash"]
    except Exception as exc:  # pragma: no cover
        return None, [f"signature verification error: {exc}"]


# ---------------------------------------------------------------------------
# Top-level verifier
# ---------------------------------------------------------------------------


def verify_gstp_package(path: str | Path, *, public_key: str | None = None) -> GstpVerificationResult:
    """Verify a GSTP package (directory) or a standalone manifest file.

    * Directory layout — expects ``manifest.json``, ``envelope.json``, optional
      ``evidence/<id>.json`` files, and (when present) ``signatures/manifest.sig``.
    * Single file — accepts a manifest JSON path; only the manifest hash is
      verified (payload and signature are skipped).
    """
    p = Path(path)
    result = GstpVerificationResult(valid=False)

    if p.is_dir():
        manifest_path = p / "manifest.json"
        if not manifest_path.is_file():
            result.issues.append(f"missing manifest.json in {p}")
            return result
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result.package_id = str(manifest.get("package_id") or "")
        result.package_type = str(manifest.get("package_type") or "")
        result.manifest_hash_ok = verify_manifest_hash(manifest)
        if not result.manifest_hash_ok:
            result.issues.append("manifest hash mismatch")
        payload_ok, payload_issues = verify_payload_hash(p)
        result.payload_hash_ok = payload_ok
        result.issues.extend(payload_issues)
        if public_key:
            sig_path = p / "signatures" / "manifest.sig"
            sig_ok, sig_warnings = _verify_signature(
                str(manifest.get("manifest_hash") or ""),
                sig_path,
                public_key,
                str(manifest.get("signature_algorithm") or "ed25519"),
            )
            result.signature_ok = sig_ok
            result.warnings.extend(sig_warnings)
            if sig_ok is False:
                result.issues.append("signature verification failed")
    elif p.is_file():
        manifest = json.loads(p.read_text(encoding="utf-8"))
        result.package_id = str(manifest.get("package_id") or "")
        result.package_type = str(manifest.get("package_type") or "")
        result.manifest_hash_ok = verify_manifest_hash(manifest)
        if not result.manifest_hash_ok:
            result.issues.append("manifest hash mismatch")
        result.warnings.append("standalone manifest verified — payload and signature checks were not performed (no package directory).")
    else:
        result.issues.append(f"not found: {p}")
        return result

    result.valid = (
        result.manifest_hash_ok
        and (result.payload_hash_ok is not False)
        and (result.signature_ok is not False)
    )
    return result


__all__ = [
    "canonical_json_bytes",
    "sha256_canonical",
    "sha256_file",
    "build_manifest",
    "verify_manifest_hash",
    "verify_payload_hash",
    "verify_gstp_package",
    "GstpVerificationResult",
]
