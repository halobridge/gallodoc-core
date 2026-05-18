"""Migration transform 1 — flat trust block (Decision 2).

v1 `trust_score.*` + v1.5 `trust_decision.*` merge into the flat v3
`trust` block with 8 same-level arrays. No nested `trust.score` or
`trust.decision`.
"""

from __future__ import annotations

from gallodoc.projection import migrate_v1_to_v3

from tests.v3_0.projection.conftest import v1_envelope_with_nested_trust


def test_flat_trust_keys_at_same_level() -> None:
    env = v1_envelope_with_nested_trust()
    out = migrate_v1_to_v3(env)
    trust = out["trust"]
    assert trust["schema_version"] == "gallodoc.trust.v3.0"
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
        assert isinstance(trust[k], list), f"trust.{k} must be a list"


def test_trust_score_components_carry_through() -> None:
    env = v1_envelope_with_nested_trust()
    out = migrate_v1_to_v3(env)
    component_names = [c.get("name") for c in out["trust"]["components"]]
    assert "evidence_coverage" in component_names
    assert "policy_alignment" in component_names


def test_trust_decision_gates_carry_through() -> None:
    env = v1_envelope_with_nested_trust()
    out = migrate_v1_to_v3(env)
    gate_ids = [g.get("gate_id") for g in out["trust"]["decision_gates"]]
    assert "gate-1" in gate_ids


def test_trust_decision_arrays_carry_through() -> None:
    env = v1_envelope_with_nested_trust()
    out = migrate_v1_to_v3(env)
    assert out["trust"]["policy_outcomes"][0]["policy_id"] == "pol-1"
    assert out["trust"]["action_recommendations"][0]["action_id"] == "act-1"
    assert out["trust"]["decision_receipts"][0]["receipt_id"] == "rcpt-1"


def test_trust_score_and_decision_keys_absent() -> None:
    env = v1_envelope_with_nested_trust()
    out = migrate_v1_to_v3(env)
    assert "trust_score" not in out
    assert "trust_decision" not in out


def test_no_nested_score_or_decision_objects() -> None:
    env = v1_envelope_with_nested_trust()
    out = migrate_v1_to_v3(env)
    assert "score" not in out["trust"]
    assert "decision" not in out["trust"]
