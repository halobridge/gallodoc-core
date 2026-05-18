"""Every committed v1.x example envelope migrates and re-validates as v3.

Loads each v1 example under `examples/gallodoc_*.json` and
`examples/v1_*/`, runs the migrator, and asserts the result validates
under the v3 validator.

If a fixture doesn't migrate cleanly, that's a real bug — the migrator
is contractually required to produce valid v3 envelopes from any v1
envelope. Tests fail loudly rather than skipping.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest

from gallodoc.projection import migrate_v1_to_v3
from gallodoc.validation import validate_envelope


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_EXAMPLES_DIR = _PACKAGE_ROOT / "examples"


def _v1_examples() -> list[Path]:
    """Collect every committed v1 example envelope path.

    Combines:
      - examples/gallodoc_*.json (the 10 v1 base reference envelopes)
      - examples/v1_*/*.json (the v1.1 / v1.2 / ... amendment examples)
    """
    paths: list[Path] = []
    paths.extend(_EXAMPLES_DIR.glob("gallodoc_*.json"))
    for sub in sorted(_EXAMPLES_DIR.glob("v1_*")):
        if sub.is_dir():
            paths.extend(sub.glob("*.json"))
    # Skip the v3 examples folder (named v3_0).
    return sorted(p for p in paths if "v3_0" not in p.parts)


_V1_EXAMPLE_PATHS = _v1_examples()


@pytest.mark.parametrize("example_path", _V1_EXAMPLE_PATHS, ids=lambda p: p.name)
def test_v1_example_migrates_and_validates(example_path: Path) -> None:
    env = json.loads(example_path.read_text(encoding="utf-8"))
    assert env.get("schema_version", "").startswith("gallodoc-core/v1"), (
        f"{example_path.name} is not a v1 envelope (schema_version="
        f"{env.get('schema_version')!r})"
    )
    migrated = migrate_v1_to_v3(env)
    assert migrated["schema_version"] == "gallodoc-core/v3"
    result = validate_envelope(migrated)
    assert result.valid, (
        f"{example_path.name} failed v3 validation after migration: "
        + "; ".join(f"{e.path}: {e.message}" for e in result.errors())
    )


def test_at_least_one_v1_example_present() -> None:
    """Smoke check — if we accidentally point at the wrong directory we'd
    parametrize zero tests and the suite would silently pass nothing."""
    assert _V1_EXAMPLE_PATHS, "no v1 examples discovered for round-trip test"
