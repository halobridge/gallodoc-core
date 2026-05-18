"""Every example envelope under ``examples/v3_0/`` must validate.

The minimal + full v3 examples validate under the v3 dispatch path; the
v1 legacy reference validates under the parallel v1 dispatch path. The
top-level ``validate_envelope`` routes both correctly by
``schema_version``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.validation import validate_envelope


PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES_V30_DIR = PACKAGE_ROOT / "examples" / "v3_0"


def _v30_examples() -> list[Path]:
    if not EXAMPLES_V30_DIR.is_dir():
        return []
    return sorted(EXAMPLES_V30_DIR.glob("*.json"))


def test_v30_examples_directory_exists() -> None:
    assert EXAMPLES_V30_DIR.is_dir(), f"examples/v3_0 must exist at {EXAMPLES_V30_DIR}"


def test_v30_examples_directory_has_three_files() -> None:
    files = _v30_examples()
    names = {p.name for p in files}
    assert names == {
        "gallodoc_minimal_reference.json",
        "gallodoc_full_v3_reference.json",
        "gallodoc_v1_legacy_reference.json",
    }, f"unexpected v3_0 example set: {names}"


@pytest.mark.parametrize(
    "example_path",
    _v30_examples(),
    ids=lambda p: p.name,
)
def test_v30_example_validates(example_path: Path) -> None:
    env = json.loads(example_path.read_text(encoding="utf-8"))
    result = validate_envelope(env)
    assert result.valid, (
        f"{example_path.name} must validate: "
        + "; ".join(f"{i.path}={i.message}" for i in result.errors()[:5])
    )
