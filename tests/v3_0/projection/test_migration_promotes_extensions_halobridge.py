"""Migration transform 3 — Q5 fix: promote v1.2–v1.6 blocks to top level.

For each name in `V12_V16_COMPLIANCE_BLOCKS` (13 names — federation
excluded):

- Extensions-only -> top level + extensions copy deleted.
- Both top-level + extensions -> top-level wins; extensions deleted.

federation is NOT promoted (v3-new; only valid at top level per
Decision 4) — the projector strips it under extensions.halobridge but
the migrator does not move it.
"""

from __future__ import annotations

import pytest

from gallodoc.projection import migrate_v1_to_v3
from gallodoc.projection.forbidden import V12_V16_COMPLIANCE_BLOCKS

from tests.v3_0.projection.conftest import v1_envelope_with_halobridge_block


# trust_decision is in the 13-name set but it's also the v1.5 source for the
# flat trust merge (Transform 1). The migrator folds its content into the
# flat trust block rather than promoting it to a top-level `trust_decision`
# key. The other 12 blocks are pure top-level promotions.
_TOP_LEVEL_PROMOTION_TARGETS = sorted(V12_V16_COMPLIANCE_BLOCKS - {"trust_decision"})


@pytest.mark.parametrize("block_name", _TOP_LEVEL_PROMOTION_TARGETS)
def test_extensions_only_promotes_to_top_level(block_name: str) -> None:
    env = v1_envelope_with_halobridge_block(block_name, {"marker": f"only-in-ext-{block_name}"})
    out = migrate_v1_to_v3(env)
    assert block_name in out, f"top-level {block_name} should exist after migration"
    assert out[block_name]["marker"] == f"only-in-ext-{block_name}"
    # extensions.halobridge.<name> must be gone.
    halobridge = (out.get("extensions") or {}).get("halobridge") or {}
    assert block_name not in halobridge


@pytest.mark.parametrize("block_name", _TOP_LEVEL_PROMOTION_TARGETS)
def test_top_level_wins_when_both_exist(block_name: str) -> None:
    env = v1_envelope_with_halobridge_block(
        block_name,
        {"marker": f"in-ext-{block_name}", "version": "stale"},
    )
    env[block_name] = {"marker": f"top-level-{block_name}", "version": "canonical"}
    out = migrate_v1_to_v3(env)
    # Top-level survives; extensions copy is gone.
    assert out[block_name]["marker"] == f"top-level-{block_name}"
    assert out[block_name]["version"] == "canonical"
    halobridge = (out.get("extensions") or {}).get("halobridge") or {}
    assert block_name not in halobridge


def test_trust_decision_under_extensions_folds_into_flat_trust() -> None:
    """`extensions.halobridge.trust_decision` is drained into the flat trust block.

    Unlike the other 12 v1.2–v1.6 blocks (which promote to top-level),
    trust_decision is the v1.5 source for the flat trust merge. The
    migrator folds its `gates` / `policy_outcomes` / etc. into the v3
    trust block instead of promoting it as a top-level key.
    """
    env = v1_envelope_with_halobridge_block(
        "trust_decision",
        {
            "gates": [{"gate_id": "from-ext", "verdict": "pass"}],
            "policy_outcomes": [],
            "action_recommendations": [],
            "decision_receipts": [],
        },
    )
    out = migrate_v1_to_v3(env)
    # NOT promoted to top-level.
    assert "trust_decision" not in out
    # Drained into flat trust.
    gate_ids = [g.get("gate_id") for g in out["trust"]["decision_gates"]]
    assert "from-ext" in gate_ids
    halobridge = (out.get("extensions") or {}).get("halobridge") or {}
    assert "trust_decision" not in halobridge


def test_federation_under_extensions_not_promoted() -> None:
    """federation is v3-new; the migrator does NOT promote it from extensions."""
    env = v1_envelope_with_halobridge_block("federation", {"some": "shape"})
    out = migrate_v1_to_v3(env)
    # Migrator does NOT touch federation — the validator/projector are the
    # gates that catch it. Confirm the migrator preserves what it doesn't
    # know how to promote.
    halobridge = (out.get("extensions") or {}).get("halobridge") or {}
    assert "federation" in halobridge
    # Top-level federation NOT created.
    assert "federation" not in out


def test_empty_halobridge_namespace_dropped() -> None:
    env = v1_envelope_with_halobridge_block("attestations", {"foo": "bar"})
    out = migrate_v1_to_v3(env)
    halobridge = (out.get("extensions") or {}).get("halobridge")
    # The only key under halobridge was attestations; after promotion the
    # namespace is empty and should be dropped from extensions.
    assert halobridge is None or halobridge == {}


def test_other_vendor_extensions_preserved() -> None:
    env = v1_envelope_with_halobridge_block("attestations", {"foo": "bar"})
    env["extensions"]["acme"] = {"private_summary": {"shape": "ok"}}
    out = migrate_v1_to_v3(env)
    assert out["extensions"]["acme"]["private_summary"]["shape"] == "ok"
    # attestations promoted up.
    assert "attestations" in out


def test_non_v12_v16_halobridge_keys_preserved() -> None:
    """Vendor-private halobridge keys (not in the 14-banned set) are preserved."""
    env = v1_envelope_with_halobridge_block("private_summary", {"foo": "bar"})
    out = migrate_v1_to_v3(env)
    halobridge = (out.get("extensions") or {}).get("halobridge") or {}
    assert "private_summary" in halobridge
