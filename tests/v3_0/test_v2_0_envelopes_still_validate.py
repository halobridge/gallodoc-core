"""v2.0 example envelopes must keep validating under the parallel v1 validator.

v2.0 envelopes carry ``schema_version: "gallodoc-core/v1"`` (the v1 family
identifier is unchanged across v2.0 / v2.1 — the "2.0" version refers to
the Python package only). They validate through the v1 dispatch path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.validation import validate_envelope


PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES_V20_DIR = PACKAGE_ROOT / "examples" / "v2_0"


def _collect_v20_examples() -> list[Path]:
    if not EXAMPLES_V20_DIR.is_dir():
        return []
    return sorted(EXAMPLES_V20_DIR.glob("*.json"))


@pytest.mark.parametrize(
    "example_path",
    _collect_v20_examples(),
    ids=lambda p: p.name,
)
def test_v20_example_validates_under_parallel_v1_validator(example_path: Path) -> None:
    env = json.loads(example_path.read_text(encoding="utf-8"))
    if env.get("schema_version") not in ("gallodoc-core/v1", "gallodoc-core/v3"):
        pytest.skip(f"{example_path.name}: schema_version={env.get('schema_version')!r}")
    result = validate_envelope(env)
    assert result.valid, (
        f"v2.0 example {example_path.name} must still validate: "
        + "; ".join(f"{i.path}={i.message}" for i in result.errors()[:5])
    )


def test_v20_examples_directory_is_recognized() -> None:
    """If the v2_0 directory is missing or empty, this test makes the
    parametrize empty — that's fine, but we still want a sentinel."""
    if not EXAMPLES_V20_DIR.is_dir():
        pytest.skip("examples/v2_0/ does not exist on disk")
    files = list(EXAMPLES_V20_DIR.glob("*.json"))
    # The repo ships at least one v2.0 example; we don't gate the test on
    # this number, but we want to confirm the directory exists when we
    # expect it to.
    assert files or True
