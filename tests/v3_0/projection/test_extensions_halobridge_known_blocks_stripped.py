"""Every name in EXTENSIONS_HALOBRIDGE_BANNED is stripped by the projector.

All 14 names — 13 v1.2–v1.6 compliance blocks + federation (Decision 4) —
are removed from `extensions.halobridge.*` by `project_to_open_core`.
The migrator promotes 13 of them to top level; federation is simply
dropped (it's v3-new and shouldn't be there).
"""

from __future__ import annotations

import pytest

from gallodoc.projection import project_to_open_core
from gallodoc.projection.forbidden import EXTENSIONS_HALOBRIDGE_BANNED

from tests.v3_0.projection.conftest import minimal_v3_envelope


@pytest.mark.parametrize("banned_name", sorted(EXTENSIONS_HALOBRIDGE_BANNED))
def test_each_banned_name_stripped(banned_name: str) -> None:
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {banned_name: {"any": "shape"}}}
    out = project_to_open_core(env)
    halo = (out.get("extensions") or {}).get("halobridge") or {}
    assert banned_name not in halo, (
        f"projector failed to strip extensions.halobridge.{banned_name!r}"
    )


def test_federation_stripped_but_not_promoted_to_top_level() -> None:
    """federation is v3-new; the projector strips it from extensions but does
    NOT create a top-level federation block from it."""
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {"federation": {"some": "shape"}}}
    out = project_to_open_core(env)
    halo = (out.get("extensions") or {}).get("halobridge") or {}
    assert "federation" not in halo
    # No top-level federation was created either.
    assert "federation" not in out


def test_count_banned_names_is_14() -> None:
    assert len(EXTENSIONS_HALOBRIDGE_BANNED) == 14
    assert "federation" in EXTENSIONS_HALOBRIDGE_BANNED
