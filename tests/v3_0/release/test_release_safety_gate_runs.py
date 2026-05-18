"""Test that scripts/release_safety_gate.py runs clean on the committed tree.

Invokes the script as a subprocess, asserts exit code 0, parses
release_safety_report.json, asserts every check status is 'pass', every
supersession artifact is true, and summary.violations is empty.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_PATH = PACKAGE_ROOT / "scripts" / "release_safety_gate.py"


@pytest.fixture()
def report_path(tmp_path: Path) -> Path:
    """Write the report into a temp dir so we never pollute the working tree."""
    return tmp_path / "release_safety_report.json"


def test_release_safety_gate_script_exists() -> None:
    assert SCRIPT_PATH.is_file(), f"Missing: {SCRIPT_PATH}"


def test_release_safety_gate_help_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"--help exited {result.returncode}: {result.stderr}"
    assert "release safety gate" in result.stdout.lower()


def test_release_safety_gate_runs_clean(report_path: Path) -> None:
    """The canonical 'v3 is ready to ship' signal."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--report", str(report_path), "--quiet"],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert report_path.is_file(), (
        f"release_safety_report.json was not written. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    # Every check must pass.
    failed_checks = [c for c in report.get("checks", []) if c.get("status") != "pass"]
    assert not failed_checks, f"Failed checks: {failed_checks}"

    # Every supersession artifact must be true.
    artifacts = report.get("supersession_artifacts") or {}
    failed_artifacts = {k: v for k, v in artifacts.items() if v is not True}
    assert not failed_artifacts, f"Failed supersession artifacts: {failed_artifacts}"

    # Violations list must be empty.
    violations = (report.get("summary") or {}).get("violations") or []
    assert not violations, f"Violations: {violations}"

    # Exit code must be 0.
    assert result.returncode == 0, f"Gate exited {result.returncode}: {result.stderr}"


def test_release_safety_report_shape(report_path: Path) -> None:
    """release_safety_report.json must match the RUNBOOK §4 shape."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--report", str(report_path), "--quiet"],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["release_id"] == "v3.0.0"
    assert report["envelope_strategy"] == "rev_to_v3"
    assert report["default_schema_version"] == "gallodoc-core/v3"
    assert report["legacy_schema_versions_supported"] == ["gallodoc-core/v1"]
    assert report["development_status_classifier"] == "4 - Beta"

    expected_check_names = {
        "v3_examples_validate",
        "v1_examples_still_validate",
        "v2_0_examples_still_validate",
        "v2_1_examples_still_validate",
        "privacy_scan",
        "forbidden_subtree_scan",
        "extensions_halobridge_known_blocks_absent",
        "trust_block_flat_only",
        "linker_entries_pinned_to_suggested",
        "no_model_weights_committed",
        "reference_projector_idempotent",
        "migration_v1_to_v3_round_trip",
    }
    actual_names = {c.get("name") for c in report["checks"]}
    assert actual_names == expected_check_names, (
        f"Check name set drifted. expected={expected_check_names}, "
        f"actual={actual_names}"
    )

    expected_artifact_keys = {
        "frozen_doc_preamble_present",
        "pyproject_classifier_bumped",
        "frozen_framing_dropped_from_release_notes",
    }
    actual_artifact_keys = set(report.get("supersession_artifacts", {}).keys())
    assert actual_artifact_keys == expected_artifact_keys

    summary = report.get("summary") or {}
    assert isinstance(summary.get("examples_checked"), int)
    assert isinstance(summary.get("tests_run"), int)
    assert isinstance(summary.get("violations"), list)
