"""Round-trip the four migration example envelopes through the projector / migrator.

Any drift in the projector or migrator's output that touches the four
committed examples in `examples/v3_0/migration/` fails this test. The
expected outputs are checked into the repo so PR reviewers can read them
without running the code.
"""

from __future__ import annotations

import json
from pathlib import Path

from gallodoc.projection import migrate_v1_to_v3, project_to_open_core


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_MIGRATION_DIR = _PACKAGE_ROOT / "examples" / "v3_0" / "migration"


def _load(name: str) -> dict:
    return json.loads((_MIGRATION_DIR / name).read_text(encoding="utf-8"))


def test_producer_input_full_projects_to_projected_output_full() -> None:
    src = _load("producer_input_full.json")
    expected = _load("projected_output_full.json")
    out = project_to_open_core(src)
    assert out == expected, (
        "project_to_open_core(producer_input_full) drifted from "
        "projected_output_full.json — if this is intentional, regenerate "
        "the example file."
    )


def test_v1_to_v3_input_migrates_to_v1_to_v3_output() -> None:
    src = _load("v1_to_v3_input.json")
    expected = _load("v1_to_v3_output.json")
    out = migrate_v1_to_v3(src)
    assert out == expected, (
        "migrate_v1_to_v3(v1_to_v3_input) drifted from "
        "v1_to_v3_output.json — if this is intentional, regenerate "
        "the example file."
    )


def test_v1_to_v3_output_validates_as_v3() -> None:
    """The migration output must satisfy the v3 validator — that's the contract."""
    from gallodoc.validation import validate_envelope

    out = _load("v1_to_v3_output.json")
    result = validate_envelope(out)
    assert result.valid, (
        "v1_to_v3_output.json failed v3 validation: "
        + "; ".join(f"{e.path}: {e.message}" for e in result.errors())
    )
