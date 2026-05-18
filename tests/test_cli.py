"""Tests for the gallodoc CLI."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from gallodoc.cli.main import main


def _run(argv: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


def test_validate_returns_zero_for_example(examples_dir: Path):
    target = examples_dir / "gallodoc_pdf_contract.json"
    rc, out, _ = _run(["validate", str(target)])
    assert rc == 0
    assert "valid: True" in out


def test_validate_returns_one_for_invalid(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    rc, _, _ = _run(["validate", str(bad)])
    assert rc == 1


def test_validate_json_output(examples_dir: Path):
    target = examples_dir / "gallodoc_pdf_contract.json"
    rc, out, _ = _run(["validate", "--json", str(target)])
    payload = json.loads(out)
    assert rc == 0
    assert payload["valid"] is True
    assert payload["schema_version"] == "gallodoc-core/v1"


def test_validate_multiple_files_human_output(examples_dir: Path):
    a = examples_dir / "gallodoc_pdf_contract.json"
    b = examples_dir / "v1_3" / "gallodoc_residency_training_model_risk.json"
    rc, out, _ = _run(["validate", str(a), str(b)])
    assert rc == 0
    assert out.count("valid: True") == 2


def test_validate_multiple_files_json_output(examples_dir: Path):
    a = examples_dir / "gallodoc_pdf_contract.json"
    b = examples_dir / "v1_3" / "gallodoc_residency_training_model_risk.json"
    rc, out, _ = _run(["validate", "--json", str(a), str(b)])
    payload = json.loads(out)
    assert rc == 0
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert all(row["valid"] for row in payload)
    assert {row["file"] for row in payload} == {str(a), str(b)}


def test_inspect_prints_summary(examples_dir: Path):
    target = examples_dir / "gallodoc_pdf_contract.json"
    rc, out, _ = _run(["inspect", "--json", str(target)])
    payload = json.loads(out)
    assert rc == 0
    assert payload["schema_version"] == "gallodoc-core/v1"
    assert payload["document_id"] == "doc-pdf-contract-0001"
    assert payload["gallounit_count"] >= 1


def test_units_command_segments_sample(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("Net 30 payment terms apply.\n\nThe provider shall deliver.", encoding="utf-8")
    rc, out, _ = _run(["units", "--json", str(f)])
    payload = json.loads(out)
    assert rc == 0
    assert payload["unit_strategy"] == "gallounit_v1"
    assert len(payload["units"]) >= 2


def test_extract_command_finds_artifacts(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("Bill To: synthetic@example.com\nDue: 2026-04-30\nAmount: $1,234.56", encoding="utf-8")
    rc, out, _ = _run(["extract", "--json", str(f)])
    payload = json.loads(out)
    assert rc == 0
    types = {a["artifact_type"] for a in payload["artifacts"]}
    assert {"email", "date", "amount"} <= types


def test_gstp_verify_detects_tamper(tmp_path: Path, examples_dir: Path):
    from gallodoc.gstp import build_manifest, sha256_canonical

    env = json.loads((examples_dir / "gallodoc_pdf_contract.json").read_text(encoding="utf-8"))
    pkg_dir = tmp_path / "pkg.gstp"
    pkg_dir.mkdir()
    (pkg_dir / "envelope.json").write_text(json.dumps(env, sort_keys=True), encoding="utf-8")
    m = build_manifest(env)
    (pkg_dir / "manifest.json").write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
    rc, out, _ = _run(["gstp", "verify", "--json", str(pkg_dir)])
    payload = json.loads(out)
    assert rc == 0
    assert payload["valid"] is True

    # Tamper envelope file.
    (pkg_dir / "envelope.json").write_text("{}", encoding="utf-8")
    rc2, _, _ = _run(["gstp", "verify", "--json", str(pkg_dir)])
    assert rc2 == 1
