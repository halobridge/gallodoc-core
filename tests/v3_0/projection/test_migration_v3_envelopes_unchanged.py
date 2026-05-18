"""Passing an already-v3 envelope through `migrate_v1_to_v3` is safe.

Already-v3 envelopes should pass through with no structural damage,
and the result should be idempotent (a second pass equals the first).
"""

from __future__ import annotations

import copy

from gallodoc.projection import migrate_v1_to_v3

from tests.v3_0.projection.conftest import minimal_v3_envelope


def test_v3_envelope_passes_through_unchanged_structurally() -> None:
    env = minimal_v3_envelope()
    original = copy.deepcopy(env)
    out = migrate_v1_to_v3(env)
    # schema_version still v3.
    assert out["schema_version"] == "gallodoc-core/v3"
    # All v3 required sections still present.
    for key in original:
        assert key in out, f"v3 key {key!r} should survive migration"


def test_v3_envelope_migration_is_idempotent() -> None:
    env = minimal_v3_envelope()
    first = migrate_v1_to_v3(env)
    second = migrate_v1_to_v3(first)
    assert first == second


def test_v3_envelope_flat_trust_preserved() -> None:
    env = minimal_v3_envelope()
    out = migrate_v1_to_v3(env)
    # The minimal v3 envelope already has a flat trust block — no nested
    # score/decision should appear.
    assert "score" not in out["trust"]
    assert "decision" not in out["trust"]
    # All 8 flat arrays still present.
    for k in (
        "components",
        "drivers",
        "blockers",
        "warnings",
        "decision_gates",
        "policy_outcomes",
        "action_recommendations",
        "decision_receipts",
    ):
        assert k in out["trust"]
