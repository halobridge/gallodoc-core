"""Schema loading helpers for GalloDoc Core envelopes.

Two schema files ship in the package:

- ``gallodoc-core-v1.schema.json`` — the v1 frozen envelope. Stays on disk
  unchanged for the parallel-validation window (6 months from 2026-05-16).
- ``gallodoc-core-v3.schema.json`` — the active v3 envelope. New consumers
  default to v3.

``load_schema()`` dispatches by version string. The default is
``"gallodoc-core/v3"``; pass ``version="gallodoc-core/v1"`` for the legacy
schema.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

SCHEMA_V1_FILENAME = "gallodoc-core-v1.schema.json"
SCHEMA_V3_FILENAME = "gallodoc-core-v3.schema.json"

# Back-compat: callers that still import SCHEMA_FILENAME get v1 (which is
# what they expected before v3 shipped). New code should use the v1/v3
# constants explicitly.
SCHEMA_FILENAME = SCHEMA_V1_FILENAME

_VERSION_TO_FILENAME: dict[str, str] = {
    "gallodoc-core/v1": SCHEMA_V1_FILENAME,
    "gallodoc-core/v3": SCHEMA_V3_FILENAME,
}


@lru_cache(maxsize=2)
def load_schema(version: str = "gallodoc-core/v3") -> dict[str, Any]:
    """Return a GalloDoc Core schema as a Python dict.

    Args:
        version: Schema family identifier. One of ``"gallodoc-core/v1"`` or
            ``"gallodoc-core/v3"``. Defaults to v3 — new consumers should
            target the active spec.

    Raises:
        ValueError: if ``version`` is not a recognized schema family.
    """
    try:
        filename = _VERSION_TO_FILENAME[version]
    except KeyError as exc:
        raise ValueError(
            f"unknown schema version {version!r}; "
            f"known versions: {sorted(_VERSION_TO_FILENAME)}"
        ) from exc

    package = "gallodoc.schema"
    try:
        text = resources.files(package).joinpath(filename).read_text(encoding="utf-8")
    except (AttributeError, ModuleNotFoundError, FileNotFoundError):
        # Fallback for unusual install layouts.
        from pathlib import Path

        here = Path(__file__).parent
        text = (here / filename).read_text(encoding="utf-8")
    return json.loads(text)


def required_top_level_sections(version: str = "gallodoc-core/v3") -> list[str]:
    return list(load_schema(version).get("required") or [])


def is_frozen(version: str = "gallodoc-core/v1") -> bool:
    """Return the schema's ``frozen`` flag.

    v1's value is ``True``; v3's is ``False`` (stability is described in
    prose in the v3 master spec, not via a flag). Defaults to v1 — callers
    historically wanted "is v1 frozen?" and the answer is still yes.
    """
    return bool(load_schema(version).get("frozen"))


def frozen_version(version: str = "gallodoc-core/v1") -> str:
    """Return the schema's ``frozen_version`` field if present, else ``""``."""
    return str(load_schema(version).get("frozen_version") or "")
