"""Every v1 example envelope must keep validating after v3 ships.

The parallel v1 validator is the contract: during the 6-month deprecation
window (per Decision 1), every v1 / v1.x envelope continues to validate
unchanged.

We dispatch through the top-level ``validate_envelope`` (the new entry
point) and let it route by ``schema_version`` — exactly what real-world
callers do.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.validation import validate_envelope


PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES_DIR = PACKAGE_ROOT / "examples"


def _collect_v1_examples() -> list[Path]:
    """Top-level v1 examples ship as ``examples/gallodoc_*.json``.

    Skip examples under ``examples/conversion/`` — those are conversion
    *inputs* (raw text / json / csv), not envelopes. The
    ``json_sample/sample.json`` fixture is the known pre-existing CI
    failure being ignored per this prompt's bootstrap notes.
    """
    paths: list[Path] = []
    for path in sorted(EXAMPLES_DIR.glob("gallodoc_*.json")):
        paths.append(path)
    for subdir_name in ("v1_1", "v1_2", "v1_3", "v1_4", "v1_5", "v1_6"):
        subdir = EXAMPLES_DIR / subdir_name
        if subdir.is_dir():
            for path in sorted(subdir.glob("*.json")):
                paths.append(path)
    return paths


@pytest.mark.parametrize(
    "example_path",
    _collect_v1_examples(),
    ids=lambda p: str(p.relative_to(EXAMPLES_DIR)),
)
def test_v1_example_validates_under_parallel_v1_validator(example_path: Path) -> None:
    env = json.loads(example_path.read_text(encoding="utf-8"))
    # Every v1 / v1.x example declares schema_version=gallodoc-core/v1.
    # If a fixture lacks schema_version we skip — it's not an envelope.
    if env.get("schema_version") != "gallodoc-core/v1":
        pytest.skip(f"{example_path.name}: not a v1 envelope (schema_version={env.get('schema_version')!r})")
    result = validate_envelope(env)
    assert result.valid, (
        f"v1 example {example_path.name} must still validate: "
        + "; ".join(f"{i.path}={i.message}" for i in result.errors()[:5])
    )
