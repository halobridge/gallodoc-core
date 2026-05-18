"""Open-source projector's strip surface — vs platform-specific layering.

The open-source projector strips banned extensions.halobridge.<name>
keys and the v1.x / v2.0 per-block forbidden keys, but does NOT strip
the platform-private patterns (`policy_formula`, `halobridge_internal`,
`__internal__`). The platform projector layers its own stripping on top.

These tests assert the layering contract explicitly.
"""

from __future__ import annotations

import pytest

from gallodoc.projection import project_to_open_core
from gallodoc.projection.safety import (
    EnterpriseLeakageError,
    assert_no_enterprise_leakage,
)

from tests.v3_0.projection.conftest import minimal_v3_envelope


def test_banned_extensions_halobridge_key_stripped_by_projector() -> None:
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {"consent_ledger": {"entries": []}}}
    out = project_to_open_core(env)
    halo = (out.get("extensions") or {}).get("halobridge") or {}
    assert "consent_ledger" not in halo


def test_v1x_forbidden_key_stripped_recursively_by_projector() -> None:
    """A v1.x forbidden key like `password` is stripped wherever it appears."""
    env = minimal_v3_envelope()
    env["security"]["password"] = "synthetic-leak"
    env["activity"]["latest_events"] = [
        {"event_type": "login", "metadata": {"password": "synthetic-leak"}}
    ]
    out = project_to_open_core(env)
    assert "password" not in out["security"]
    for event in out["activity"]["latest_events"]:
        assert "password" not in (event.get("metadata") or {})


def test_platform_private_policy_formula_NOT_stripped_by_projector() -> None:
    """The open-source projector intentionally does NOT strip `policy_formula`.

    That stripping is the platform projector's responsibility per the
    layering contract documented in
    docs/specs/gallodoc-core-v3-reference-projector.md.
    """
    env = minimal_v3_envelope()
    env["activity"]["latest_events"] = [{"metadata": {"policy_formula": "if x then y"}}]
    out = project_to_open_core(env)
    # policy_formula survives.
    assert out["activity"]["latest_events"][0]["metadata"]["policy_formula"] == "if x then y"


def test_platform_private_halobridge_internal_NOT_stripped_by_projector() -> None:
    env = minimal_v3_envelope()
    env["extensions"]["acme"] = {"halobridge_internal": {"trace": "x"}}
    out = project_to_open_core(env)
    # halobridge_internal as a key under a vendor namespace survives.
    assert "halobridge_internal" in out["extensions"]["acme"]


def test_platform_private_double_underscore_internal_NOT_stripped_by_projector() -> None:
    env = minimal_v3_envelope()
    env["gallounits"]["__internal__"] = {"trace_id": "abc"}
    out = project_to_open_core(env)
    assert "__internal__" in out["gallounits"]


def test_safety_assertion_catches_what_projector_left_behind() -> None:
    """The layering contract: projector strips banned ext.halobridge keys + v1.x/v2.0
    forbidden keys; safety assertion catches platform-private patterns.

    Pass a fixture with BOTH kinds of leaks through the projector. After
    projection, the banned-extensions key is gone, BUT `policy_formula` survives.
    Calling assert_no_enterprise_leakage on the projector output MUST raise
    because policy_formula is still there.
    """
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {"consent_ledger": {"entries": []}}}
    env["activity"]["latest_events"] = [{"metadata": {"policy_formula": "if x then y"}}]
    out = project_to_open_core(env)
    # ext.halobridge.consent_ledger stripped.
    halo = (out.get("extensions") or {}).get("halobridge") or {}
    assert "consent_ledger" not in halo
    # But policy_formula survives — the projector doesn't know about it.
    assert out["activity"]["latest_events"][0]["metadata"]["policy_formula"] == "if x then y"
    # And the safety assertion catches it.
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(out)
    assert "policy_formula" in str(exc.value)
