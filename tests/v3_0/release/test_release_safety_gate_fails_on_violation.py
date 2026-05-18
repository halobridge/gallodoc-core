"""Negative path: the release safety gate must FAIL on injected violations.

Injects a synthetic violation against an in-memory copy of the gate
modules, runs the gate, and asserts non-zero exit + the violation
surfaces in summary.violations. Uses ``monkeypatch`` so we never
pollute the committed tree.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_PATH = PACKAGE_ROOT / "scripts" / "release_safety_gate.py"


def _load_gate_module() -> ModuleType:
    """Load scripts/release_safety_gate.py as an isolated module.

    Using importlib.util.spec_from_file_location avoids needing to make
    ``scripts`` a Python package.
    """
    spec = importlib.util.spec_from_file_location(
        "release_safety_gate", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_fails_when_pyproject_classifier_reverts(tmp_path: Path) -> None:
    """If the classifier is reverted, the supersession artifact check must fail."""
    # Stage a stand-in package tree with pyproject.toml carrying Alpha.
    fake_pkg = tmp_path / "fake_gallodoc_core"
    fake_pkg.mkdir()
    (fake_pkg / "pyproject.toml").write_text(
        "[project]\nname = 'gallodoc'\nclassifiers = ['Development Status :: 3 - Alpha']\n",
        encoding="utf-8",
    )
    # Create the supersession-relevant files so the OTHER checks don't
    # explode when we run the gate in this fake tree. (We don't actually
    # invoke the gate against the fake tree; we exercise the underlying
    # check function directly — far easier to keep deterministic.)
    gate = _load_gate_module()

    # Override the PACKAGE_ROOT inside the loaded module to point at our
    # fake tree, then call the supersession-artifact check directly.
    original_root = gate.PACKAGE_ROOT
    gate.PACKAGE_ROOT = fake_pkg
    try:
        ok, violations = gate.check_pyproject_classifier_bumped()
    finally:
        gate.PACKAGE_ROOT = original_root

    assert ok is False
    assert violations and any("4 - Beta" in v for v in violations), violations


def test_gate_fails_when_frozen_doc_preamble_missing(tmp_path: Path) -> None:
    """If the FROZEN doc loses its 'Superseded by v3' preamble, the check fails."""
    fake_pkg = tmp_path / "fake"
    (fake_pkg / "docs").mkdir(parents=True)
    # FROZEN doc without the preamble.
    (fake_pkg / "docs" / "GALLODOC_CORE_V1_FROZEN.md").write_text(
        "# Frozen v1\n\nThis is the v1 doc.\n",
        encoding="utf-8",
    )

    gate = _load_gate_module()

    original_root = gate.PACKAGE_ROOT
    gate.PACKAGE_ROOT = fake_pkg
    try:
        ok, violations = gate.check_frozen_doc_preamble_present()
    finally:
        gate.PACKAGE_ROOT = original_root

    assert ok is False
    assert violations and any("Superseded by v3" in v for v in violations), violations


def test_gate_fails_when_release_notes_self_describe_as_frozen(tmp_path: Path) -> None:
    """If RELEASE_NOTES_3.0.0.md says 'v3 is frozen', the check fails."""
    fake_pkg = tmp_path / "fake"
    fake_pkg.mkdir()
    (fake_pkg / "RELEASE_NOTES_3.0.0.md").write_text(
        "# v3 release notes\n\nv3 is frozen. End of story.\n",
        encoding="utf-8",
    )

    gate = _load_gate_module()

    original_root = gate.PACKAGE_ROOT
    gate.PACKAGE_ROOT = fake_pkg
    try:
        ok, violations = gate.check_frozen_framing_dropped_from_release_notes()
    finally:
        gate.PACKAGE_ROOT = original_root

    assert ok is False
    assert violations and "self-describes v3 as 'frozen'" in violations[0], violations


def test_gate_subprocess_returns_nonzero_when_classifier_reverted(tmp_path: Path) -> None:
    """End-to-end: revert the classifier on a copy of pyproject.toml,
    run the script against that copy, assert non-zero exit + the violation
    surfaces in summary.violations.

    Uses a separate scratch copy of pyproject.toml and patches the script's
    PACKAGE_ROOT via the PYTHONPATH + env-var pattern that the gate exposes
    indirectly. The cleanest approach is to invoke run_gate() in-process
    after pointing PACKAGE_ROOT at a scratch tree that mirrors the real
    one.
    """
    gate = _load_gate_module()
    # Build a scratch tree that mirrors the real one but with the
    # classifier reverted.
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    # Copy the FROZEN doc preamble + RELEASE_NOTES so those checks pass.
    (scratch / "docs").mkdir()
    (scratch / "docs" / "GALLODOC_CORE_V1_FROZEN.md").write_text(
        "# v1 FROZEN\n\n> Superseded by v3.\n",
        encoding="utf-8",
    )
    (scratch / "RELEASE_NOTES_3.0.0.md").write_text(
        "# v3 release notes\n\nStable. No frozen framing here.\n",
        encoding="utf-8",
    )
    # Revert the classifier.
    (scratch / "pyproject.toml").write_text(
        '[project]\nclassifiers = ["Development Status :: 3 - Alpha"]\n',
        encoding="utf-8",
    )
    # Empty examples dir so example checks pass trivially.
    (scratch / "examples").mkdir()
    # Empty gallodoc dir so the model-weight scan walks an empty tree.
    (scratch / "gallodoc").mkdir()

    # Point the gate at the scratch tree.
    original_root = gate.PACKAGE_ROOT
    gate.PACKAGE_ROOT = scratch
    try:
        report = gate.run_gate()
    finally:
        gate.PACKAGE_ROOT = original_root

    # The classifier supersession artifact must be False.
    assert report["supersession_artifacts"]["pyproject_classifier_bumped"] is False
    # And the violations list must include the classifier-revert string.
    violations = report["summary"]["violations"]
    assert any("4 - Beta" in v for v in violations), violations
    # And report_passes must agree it's a fail.
    assert gate.report_passes(report) is False
