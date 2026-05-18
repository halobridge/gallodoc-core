"""Smoke test: every CLI subcommand + release script entrypoint is invokable.

Each subcommand is exercised with ``--help`` and asserted to exit 0.
This is a fast trip-wire — if a subparser is removed or renamed by
accident, this test surfaces it immediately.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ---------------------------------------------------------------------------
# CLI subcommand smoke tests
# ---------------------------------------------------------------------------


GALLODOC_HELP_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("--help",),
    ("validate", "--help"),
    ("inspect", "--help"),
    ("connector", "convert", "--help"),
    ("semantic", "embed", "--help"),
    ("training", "export-pairs", "--help"),
    ("federation", "match", "--help"),
    ("aibi", "plan", "--help"),
)


def _run_module_cli(args: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "gallodoc.cli.main", *args],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("args", GALLODOC_HELP_COMMANDS, ids=lambda a: " ".join(a))
def test_gallodoc_cli_help(args: tuple[str, ...]) -> None:
    """Each `gallodoc <subcommand> --help` exits 0."""
    result = _run_module_cli(args)
    assert result.returncode == 0, (
        f"`gallodoc {' '.join(args)}` exited {result.returncode}.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    # argparse prints usage to stdout for --help; sanity check.
    assert result.stdout, f"`gallodoc {' '.join(args)} --help` produced no stdout"


# ---------------------------------------------------------------------------
# Release script smoke tests
# ---------------------------------------------------------------------------


SCRIPT_HELP_COMMANDS: tuple[tuple[Path, str], ...] = (
    (PACKAGE_ROOT / "scripts" / "release_safety_gate.py", "release safety gate"),
    (PACKAGE_ROOT / "scripts" / "train_gallodoc_embedder.py", "train"),
    (PACKAGE_ROOT / "scripts" / "evaluate_gallodoc_embedder.py", "evaluate"),
)


@pytest.mark.parametrize(
    "script_path,marker",
    SCRIPT_HELP_COMMANDS,
    ids=[p.name for p, _ in SCRIPT_HELP_COMMANDS],
)
def test_release_script_help_exits_zero(script_path: Path, marker: str) -> None:
    """Each release script supports --help and exits 0."""
    assert script_path.is_file(), f"Missing: {script_path}"
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"`{script_path.name} --help` exited {result.returncode}.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert marker.lower() in result.stdout.lower(), (
        f"`{script_path.name} --help` stdout missing marker {marker!r}: "
        f"{result.stdout[:200]!r}"
    )
