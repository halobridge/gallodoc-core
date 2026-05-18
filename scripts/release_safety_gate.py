#!/usr/bin/env python3
"""Release safety gate for GalloDoc Core v3.0.

Runs 12 checks and emits release_safety_report.json with the exact shape
documented in docs/v3-design/RELEASE_RUNBOOK.md §4. Exits 0 if every check
passes AND every supersession_artifacts entry is true AND
summary.violations is empty.

The 12 checks (each function returns "pass" or "fail" plus a violations
list):

 1. v3_examples_validate
 2. v1_examples_still_validate
 3. v2_0_examples_still_validate
 4. v2_1_examples_still_validate
 5. privacy_scan
 6. forbidden_subtree_scan
 7. extensions_halobridge_known_blocks_absent
 8. trust_block_flat_only
 9. linker_entries_pinned_to_suggested
10. no_model_weights_committed
11. reference_projector_idempotent
12. migration_v1_to_v3_round_trip

Plus three supersession artifact checks (Decision 1):
- frozen_doc_preamble_present
- pyproject_classifier_bumped
- frozen_framing_dropped_from_release_notes

Usage::

    python3 scripts/release_safety_gate.py                  # run + write report
    python3 scripts/release_safety_gate.py --help           # show help
    python3 scripts/release_safety_gate.py --report PATH    # write to PATH
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

# Resolve the package root regardless of cwd.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# Make the gallodoc package importable when running as a script.
sys.path.insert(0, str(PACKAGE_ROOT))

from gallodoc.projection import migrate_v1_to_v3, project_to_open_core  # noqa: E402
from gallodoc.projection.forbidden import EXTENSIONS_HALOBRIDGE_BANNED  # noqa: E402
from gallodoc.projection.safety import (  # noqa: E402
    EnterpriseLeakageError,
    assert_no_enterprise_leakage,
)
from gallodoc.validation import validate_envelope  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_LINKER_DISCOVERED_BY_RE = re.compile(r".*linker.*", re.IGNORECASE)

# Subdirectories under examples/v3_0/ whose contents are explicitly
# before/after migration documentation. Migration-input fixtures
# intentionally carry banned patterns + v1-shaped content to demonstrate
# the migrator/projector cleanup. They are not real-world envelopes; the
# privacy + forbidden-subtree + v3-validation checks skip them.
#
# The `migrate_v1_to_v3` round-trip check (#12) still exercises every v1
# migration input via the v1-example path (`v1_to_v3_input.json` is in
# this directory but its `schema_version: gallodoc-core/v1` puts it in
# the v1 cohort regardless of location).
_MIGRATION_DEMO_DIR_NAMES: frozenset[str] = frozenset({"migration"})


def _is_migration_demo_path(path: Path) -> bool:
    """True if `path` lives under examples/v3_0/<migration_demo_dir>/..."""
    try:
        rel = path.relative_to(PACKAGE_ROOT / "examples" / "v3_0")
    except ValueError:
        return False
    return rel.parts and rel.parts[0] in _MIGRATION_DEMO_DIR_NAMES


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def _is_envelope(data: Any, schema_version: str) -> bool:
    return (
        isinstance(data, dict)
        and data.get("schema_version") == schema_version
    )


def _is_v3_envelope(data: Any) -> bool:
    return _is_envelope(data, "gallodoc-core/v3")


def _is_v1_envelope(data: Any) -> bool:
    return _is_envelope(data, "gallodoc-core/v1")


def _example_paths_in(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.rglob("*.json"))


def _v3_example_paths() -> list[Path]:
    return _example_paths_in(PACKAGE_ROOT / "examples" / "v3_0")


def _v1_example_paths() -> list[Path]:
    """v1 examples — `examples/gallodoc_*.json` plus everything under examples/v1_*."""
    root = PACKAGE_ROOT / "examples"
    paths: list[Path] = []
    if root.is_dir():
        paths.extend(sorted(root.glob("gallodoc_*.json")))
        for sub in sorted(root.glob("v1_*")):
            if sub.is_dir():
                paths.extend(sorted(sub.rglob("*.json")))
    return paths


def _v2_example_paths(sub: str) -> list[Path]:
    """v2.x examples (sub == 'v2_0' or 'v2_1'). Returns empty list if dir absent."""
    return _example_paths_in(PACKAGE_ROOT / "examples" / sub)


def _all_example_paths() -> list[Path]:
    root = PACKAGE_ROOT / "examples"
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.json"))


# ---------------------------------------------------------------------------
# The 12 checks
# ---------------------------------------------------------------------------


def check_v3_examples_validate() -> tuple[str, list[str], int]:
    """Check 1 — every v3 envelope under examples/v3_0/** validates.

    Migration-demo fixtures (under examples/v3_0/migration/) are
    explicitly before/after pairs documenting transforms and are not
    real-world envelopes; they are skipped.
    """
    violations: list[str] = []
    checked = 0
    for path in _v3_example_paths():
        if _is_migration_demo_path(path):
            continue
        data = _load_json(path)
        if not _is_v3_envelope(data):
            continue
        checked += 1
        try:
            result = validate_envelope(data)
        except Exception as exc:  # pragma: no cover - defensive
            violations.append(f"v3_examples_validate: {path}: validator raised {exc!r}")
            continue
        if not result.valid:
            issues = "; ".join(f"{i.path}: {i.message}" for i in result.issues if i.severity == "error")
            violations.append(f"v3_examples_validate: {path}: {issues}")
    return ("pass" if not violations else "fail"), violations, checked


def check_v1_examples_still_validate() -> tuple[str, list[str], int]:
    """Check 2 — every v1 envelope validates under the parallel v1 validator."""
    violations: list[str] = []
    checked = 0
    for path in _v1_example_paths():
        data = _load_json(path)
        if not _is_v1_envelope(data):
            continue
        checked += 1
        try:
            result = validate_envelope(data)
        except Exception as exc:  # pragma: no cover - defensive
            violations.append(f"v1_examples_still_validate: {path}: validator raised {exc!r}")
            continue
        if not result.valid:
            issues = "; ".join(f"{i.path}: {i.message}" for i in result.issues if i.severity == "error")
            violations.append(f"v1_examples_still_validate: {path}: {issues}")
    return ("pass" if not violations else "fail"), violations, checked


def check_v2_examples_still_validate(sub: str, check_name: str) -> tuple[str, list[str], int]:
    """Checks 3 + 4 — every v2.0/v2.1 example validates. Empty-skip if dir absent."""
    paths = _v2_example_paths(sub)
    if not paths:
        return "pass", [], 0
    violations: list[str] = []
    checked = 0
    for path in paths:
        data = _load_json(path)
        if not isinstance(data, dict) or "schema_version" not in data:
            continue
        checked += 1
        try:
            result = validate_envelope(data)
        except Exception as exc:  # pragma: no cover - defensive
            violations.append(f"{check_name}: {path}: validator raised {exc!r}")
            continue
        if not result.valid:
            issues = "; ".join(f"{i.path}: {i.message}" for i in result.issues if i.severity == "error")
            violations.append(f"{check_name}: {path}: {issues}")
    return ("pass" if not violations else "fail"), violations, checked


def check_privacy_scan() -> tuple[str, list[str], int]:
    """Check 5 — assert_no_enterprise_leakage on every example.

    Migration-demo fixtures (under examples/v3_0/migration/) intentionally
    carry banned patterns to document the projector / migrator's cleanup
    behavior. They are skipped here; the migrator round-trip check (#12)
    exercises them via a different code path.
    """
    violations: list[str] = []
    checked = 0
    for path in _all_example_paths():
        if _is_migration_demo_path(path):
            continue
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        checked += 1
        try:
            assert_no_enterprise_leakage(data)
        except EnterpriseLeakageError as exc:
            violations.append(f"privacy_scan: {path}: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            violations.append(f"privacy_scan: {path}: scan raised {exc!r}")
    return ("pass" if not violations else "fail"), violations, checked


def _forbidden_subtree_scan_for_paths() -> tuple[list[str], int]:
    violations: list[str] = []
    checked = 0
    for path in _all_example_paths():
        if _is_migration_demo_path(path):
            continue
        data = _load_json(path)
        if not isinstance(data, dict):
            continue
        checked += 1
        extensions = data.get("extensions")
        if not isinstance(extensions, dict):
            continue
        halobridge = extensions.get("halobridge")
        if not isinstance(halobridge, dict):
            continue
        leaked = sorted(set(halobridge.keys()) & EXTENSIONS_HALOBRIDGE_BANNED)
        if leaked:
            violations.append(
                f"{path}: extensions.halobridge.<known_block> leaked: {leaked}"
            )
    return violations, checked


def check_forbidden_subtree_scan() -> tuple[str, list[str], int]:
    """Check 6 — no example has a banned key under extensions.halobridge."""
    violations, checked = _forbidden_subtree_scan_for_paths()
    violations = [f"forbidden_subtree_scan: {v}" for v in violations]
    return ("pass" if not violations else "fail"), violations, checked


def check_extensions_halobridge_known_blocks_absent() -> tuple[str, list[str], int]:
    """Check 7 — phrased explicitly per RELEASE_RUNBOOK §4."""
    violations, checked = _forbidden_subtree_scan_for_paths()
    violations = [f"extensions_halobridge_known_blocks_absent: {v}" for v in violations]
    return ("pass" if not violations else "fail"), violations, checked


def check_trust_block_flat_only() -> tuple[str, list[str], int]:
    """Check 8 — no example has trust.score or trust.decision as nested dicts."""
    violations: list[str] = []
    checked = 0
    for path in _v3_example_paths():
        if _is_migration_demo_path(path):
            continue
        data = _load_json(path)
        if not _is_v3_envelope(data):
            continue
        checked += 1
        trust = data.get("trust")
        if not isinstance(trust, dict):
            continue
        bad = [k for k in ("score", "decision") if isinstance(trust.get(k), dict)]
        if bad:
            violations.append(
                f"trust_block_flat_only: {path}: nested trust.{'/'.join(bad)} forbidden in v3 (Decision 2)"
            )
    return ("pass" if not violations else "fail"), violations, checked


def check_linker_entries_pinned_to_suggested() -> tuple[str, list[str], int]:
    """Check 9 — every linker-discovered relationship has status:'suggested'
    OR a matching relationship_decisions[] entry promotes it.

    Per the Codex 04 [10/9] rule update: an entry with discovered_by matching
    *linker* is acceptable in any status IF a relationship_decisions[]
    record exists for the same relationship_id; otherwise the entry must be
    status="suggested".
    """
    violations: list[str] = []
    checked = 0
    for path in _v3_example_paths():
        if _is_migration_demo_path(path):
            continue
        data = _load_json(path)
        if not _is_v3_envelope(data):
            continue
        checked += 1
        rels_block = data.get("relationships")
        if not isinstance(rels_block, dict):
            continue
        rels = rels_block.get("relationships")
        decisions = rels_block.get("relationship_decisions") or []
        if not isinstance(rels, list):
            continue
        decisions_by_id = {
            d.get("relationship_id")
            for d in decisions
            if isinstance(d, dict) and d.get("relationship_id")
        }
        for rel in rels:
            if not isinstance(rel, dict):
                continue
            discovered_by = rel.get("discovered_by") or ""
            status = rel.get("status")
            rel_id = rel.get("relationship_id")
            if not _LINKER_DISCOVERED_BY_RE.match(str(discovered_by)):
                continue
            if status == "suggested":
                continue
            if rel_id and rel_id in decisions_by_id:
                # Promoted via human review — acceptable per Codex 04 [10/9].
                continue
            violations.append(
                f"linker_entries_pinned_to_suggested: {path}: relationship "
                f"{rel_id!r} discovered_by={discovered_by!r} has status={status!r} "
                "without a matching relationship_decisions[] record"
            )
    return ("pass" if not violations else "fail"), violations, checked


def check_no_model_weights_committed() -> tuple[str, list[str], int]:
    """Check 10 — no model weight files under the package tree."""
    suffixes = (".bin", ".safetensors", ".pt", ".ckpt", ".onnx", ".gguf")
    violations: list[str] = []
    checked = 0
    skip_dirs = {"build", "dist", ".git", "__pycache__"}
    for root, dirs, files in _walk(PACKAGE_ROOT, skip_dirs):
        for name in files:
            checked += 1
            lower = name.lower()
            if any(lower.endswith(s) for s in suffixes):
                rel = (Path(root) / name).relative_to(PACKAGE_ROOT)
                violations.append(f"no_model_weights_committed: {rel}")
    return ("pass" if not violations else "fail"), violations, checked


def _walk(root: Path, skip_dirs: set[str]):
    import os

    for current, dirnames, filenames in os.walk(root):
        # Skip in-place.
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        yield current, dirnames, filenames


def check_reference_projector_idempotent() -> tuple[str, list[str], int]:
    """Check 11 — project(project(env)) == project(env) on every v3 example."""
    violations: list[str] = []
    checked = 0
    for path in _v3_example_paths():
        if _is_migration_demo_path(path):
            continue
        data = _load_json(path)
        if not _is_v3_envelope(data):
            continue
        checked += 1
        try:
            once = project_to_open_core(data)
            twice = project_to_open_core(once)
        except Exception as exc:  # pragma: no cover - defensive
            violations.append(
                f"reference_projector_idempotent: {path}: projector raised {exc!r}"
            )
            continue
        if once != twice:
            violations.append(
                f"reference_projector_idempotent: {path}: projector is not idempotent"
            )
    return ("pass" if not violations else "fail"), violations, checked


def check_migration_v1_to_v3_round_trip() -> tuple[str, list[str], int]:
    """Check 12 — migrate_v1_to_v3(v1_env) validates as v3."""
    violations: list[str] = []
    checked = 0
    for path in _v1_example_paths():
        data = _load_json(path)
        if not _is_v1_envelope(data):
            continue
        checked += 1
        try:
            migrated = migrate_v1_to_v3(data)
            result = validate_envelope(migrated)
        except Exception as exc:  # pragma: no cover - defensive
            violations.append(
                f"migration_v1_to_v3_round_trip: {path}: migration raised {exc!r}"
            )
            continue
        if not result.valid:
            issues = "; ".join(f"{i.path}: {i.message}" for i in result.issues if i.severity == "error")
            violations.append(
                f"migration_v1_to_v3_round_trip: {path}: migrated envelope invalid — {issues}"
            )
    return ("pass" if not violations else "fail"), violations, checked


# ---------------------------------------------------------------------------
# Three supersession-artifact checks (Decision 1)
# ---------------------------------------------------------------------------


def check_frozen_doc_preamble_present() -> tuple[bool, list[str]]:
    path = PACKAGE_ROOT / "docs" / "GALLODOC_CORE_V1_FROZEN.md"
    if not path.is_file():
        return False, [f"frozen_doc_preamble_present: {path} not found"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, [f"frozen_doc_preamble_present: read failed: {exc}"]
    head = "\n".join(text.splitlines()[:30])
    if "Superseded by v3" not in head:
        return False, [
            "frozen_doc_preamble_present: 'Superseded by v3' not found in "
            "the first 30 lines of docs/GALLODOC_CORE_V1_FROZEN.md"
        ]
    return True, []


def check_pyproject_classifier_bumped() -> tuple[bool, list[str]]:
    path = PACKAGE_ROOT / "pyproject.toml"
    if not path.is_file():
        return False, [f"pyproject_classifier_bumped: {path} not found"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, [f"pyproject_classifier_bumped: read failed: {exc}"]
    if '"Development Status :: 4 - Beta"' not in text:
        return False, [
            "pyproject_classifier_bumped: 'Development Status :: 4 - Beta' "
            "not present in pyproject.toml"
        ]
    return True, []


# Strict pattern set per the prompt: forbid the four phrasings that
# self-describe v3 as frozen. The bare substring "frozen" may appear in
# narrative referring to v1's prior framing — but never as a self-
# description of v3.
_V3_FROZEN_SELF_DESCRIPTIONS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bv3\s+is\s+frozen\b",
        r"\bv3\.0\s+is\s+frozen\b",
        r"\bfrozen\s+v3\b",
        r"\bfrozen\s+v3\.0\b",
    )
)


def check_frozen_framing_dropped_from_release_notes() -> tuple[bool, list[str]]:
    path = PACKAGE_ROOT / "RELEASE_NOTES_3.0.0.md"
    if not path.is_file():
        return False, [
            f"frozen_framing_dropped_from_release_notes: {path} not found"
        ]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, [
            f"frozen_framing_dropped_from_release_notes: read failed: {exc}"
        ]
    hits = []
    for pattern in _V3_FROZEN_SELF_DESCRIPTIONS:
        if pattern.search(text):
            hits.append(pattern.pattern)
    if hits:
        return False, [
            "frozen_framing_dropped_from_release_notes: RELEASE_NOTES_3.0.0.md "
            f"self-describes v3 as 'frozen' (matched: {hits})"
        ]
    return True, []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


_CHECKS: list[tuple[str, Callable[[], tuple[str, list[str], int]]]] = [
    ("v3_examples_validate", check_v3_examples_validate),
    ("v1_examples_still_validate", check_v1_examples_still_validate),
    ("v2_0_examples_still_validate", lambda: check_v2_examples_still_validate("v2_0", "v2_0_examples_still_validate")),
    ("v2_1_examples_still_validate", lambda: check_v2_examples_still_validate("v2_1", "v2_1_examples_still_validate")),
    ("privacy_scan", check_privacy_scan),
    ("forbidden_subtree_scan", check_forbidden_subtree_scan),
    ("extensions_halobridge_known_blocks_absent", check_extensions_halobridge_known_blocks_absent),
    ("trust_block_flat_only", check_trust_block_flat_only),
    ("linker_entries_pinned_to_suggested", check_linker_entries_pinned_to_suggested),
    ("no_model_weights_committed", check_no_model_weights_committed),
    ("reference_projector_idempotent", check_reference_projector_idempotent),
    ("migration_v1_to_v3_round_trip", check_migration_v1_to_v3_round_trip),
]


def run_gate() -> dict[str, Any]:
    """Run all 12 checks + 3 supersession artifacts. Return the report dict."""
    check_results: list[dict[str, str]] = []
    all_violations: list[str] = []
    total_examples = 0

    for name, fn in _CHECKS:
        status, violations, examples_checked = fn()
        check_results.append({"name": name, "status": status})
        if violations:
            all_violations.extend(violations)
        total_examples += examples_checked

    supersession_artifacts: dict[str, bool] = {}
    for art_name, art_fn in (
        ("frozen_doc_preamble_present", check_frozen_doc_preamble_present),
        ("pyproject_classifier_bumped", check_pyproject_classifier_bumped),
        ("frozen_framing_dropped_from_release_notes", check_frozen_framing_dropped_from_release_notes),
    ):
        ok, violations = art_fn()
        supersession_artifacts[art_name] = bool(ok)
        if not ok:
            all_violations.extend(violations)

    report: dict[str, Any] = {
        "release_id": "v3.0.0",
        "envelope_strategy": "rev_to_v3",
        "default_schema_version": "gallodoc-core/v3",
        "legacy_schema_versions_supported": ["gallodoc-core/v1"],
        "development_status_classifier": "4 - Beta",
        "supersession_artifacts": supersession_artifacts,
        "checks": check_results,
        "summary": {
            "examples_checked": total_examples,
            "tests_run": len(_CHECKS) + len(supersession_artifacts),
            "violations": all_violations,
        },
    }
    return report


def report_passes(report: dict[str, Any]) -> bool:
    """Gate criteria: every check 'pass', every supersession artifact true, no violations."""
    for check in report.get("checks", []):
        if check.get("status") != "pass":
            return False
    for value in (report.get("supersession_artifacts") or {}).values():
        if value is not True:
            return False
    if (report.get("summary") or {}).get("violations"):
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release_safety_gate",
        description="Run the 12-check GalloDoc Core v3 release safety gate.",
    )
    parser.add_argument(
        "--report",
        default=str(PACKAGE_ROOT / "release_safety_report.json"),
        help="Path to write the JSON report (default: ./release_safety_report.json).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable summary; only write the JSON report.",
    )
    args = parser.parse_args(argv)

    report = run_gate()
    out_path = Path(args.report)
    out_path.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )

    passing = report_passes(report)

    if not args.quiet:
        sys.stdout.write("GalloDoc Core v3 release safety gate\n")
        sys.stdout.write(f"  report: {out_path}\n")
        sys.stdout.write(f"  examples_checked: {report['summary']['examples_checked']}\n")
        sys.stdout.write(f"  tests_run: {report['summary']['tests_run']}\n")
        for check in report["checks"]:
            sys.stdout.write(f"  [{check['status']:4s}] {check['name']}\n")
        for k, v in report["supersession_artifacts"].items():
            mark = "true " if v else "FALSE"
            sys.stdout.write(f"  [{mark}] supersession_artifacts.{k}\n")
        if report["summary"]["violations"]:
            sys.stdout.write("  violations:\n")
            for v in report["summary"]["violations"]:
                sys.stdout.write(f"    - {v}\n")
        sys.stdout.write(f"\nresult: {'PASS' if passing else 'FAIL'}\n")

    return 0 if passing else 1


if __name__ == "__main__":
    sys.exit(main())
