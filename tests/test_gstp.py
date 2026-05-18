"""Tests for the GSTP open-core verification shell."""

from __future__ import annotations

import json
from pathlib import Path

from gallodoc.gstp import (
    build_manifest,
    canonical_json_bytes,
    sha256_canonical,
    verify_gstp_package,
    verify_manifest_hash,
)


def test_canonical_json_is_stable():
    a = canonical_json_bytes({"b": 1, "a": 2})
    b = canonical_json_bytes({"a": 2, "b": 1})
    assert a == b


def test_sha256_canonical_returns_prefix():
    h = sha256_canonical({"x": 1})
    assert h.startswith("sha256:")


def test_build_manifest_recomputes_manifest_hash(example_envelopes):
    env = next(iter(example_envelopes.values()))
    m = build_manifest(env)
    assert m["manifest_hash"].startswith("sha256:")
    assert verify_manifest_hash(m) is True


def test_verify_detects_tampered_manifest(example_envelopes):
    env = next(iter(example_envelopes.values()))
    m = build_manifest(env)
    # Tamper.
    m["package_id"] = "tampered"
    assert verify_manifest_hash(m) is False


def test_verify_gstp_package_directory(tmp_path: Path, example_envelopes):
    env = next(iter(example_envelopes.values()))
    pkg_dir = tmp_path / "pkg.gstp"
    pkg_dir.mkdir()
    env_path = pkg_dir / "envelope.json"
    env_path.write_text(json.dumps(env, sort_keys=True), encoding="utf-8")
    m = build_manifest(env)
    (pkg_dir / "manifest.json").write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
    result = verify_gstp_package(pkg_dir)
    assert result.manifest_hash_ok is True
    assert result.payload_hash_ok is True
    assert result.valid is True


def test_verify_standalone_manifest_warns_about_payload(tmp_path: Path, example_envelopes):
    env = next(iter(example_envelopes.values()))
    m = build_manifest(env)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
    result = verify_gstp_package(p)
    assert result.manifest_hash_ok is True
    assert result.payload_hash_ok is None
    assert any("standalone manifest" in w for w in result.warnings)
