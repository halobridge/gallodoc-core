"""v3 validator rule 3: the ``trust`` block is flat.

Per Decision 2 in docs/v3-design/07_decisions.md, nested ``trust.score`` or
``trust.decision`` objects are forbidden — they are v1.5 carry-overs from
tools that have not been upgraded.
"""

from __future__ import annotations

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


def test_flat_trust_block_validates() -> None:
    env = minimal_v3_envelope()
    env["trust"] = {
        "schema_version": "gallodoc.trust.v3.0",
        "components": [],
        "drivers": ["evidence_quality_high"],
        "blockers": [],
        "warnings": [],
        "decision_gates": [],
        "policy_outcomes": [],
        "action_recommendations": [],
        "decision_receipts": [],
    }
    result = validate_envelope(env)
    assert result.valid, f"flat trust block should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_nested_trust_score_rejected() -> None:
    env = minimal_v3_envelope()
    env["trust"]["score"] = {"score": 87.5, "grade": "B"}
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i
        for i in result.errors()
        if i.path == "trust.score" and "flat" in i.message
    ]
    assert matching, f"expected trust.score flat-rule issue, got {[(i.path, i.message) for i in result.errors()]}"


def test_nested_trust_decision_rejected() -> None:
    env = minimal_v3_envelope()
    env["trust"]["decision"] = {"decision_gates": [], "policy_outcomes": []}
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i
        for i in result.errors()
        if i.path == "trust.decision" and "flat" in i.message
    ]
    assert matching, f"expected trust.decision flat-rule issue, got {[(i.path, i.message) for i in result.errors()]}"


def test_both_nested_objects_both_rejected() -> None:
    env = minimal_v3_envelope()
    env["trust"]["score"] = {"score": 0}
    env["trust"]["decision"] = {"decision_gates": []}
    result = validate_envelope(env)
    assert not result.valid
    score_issues = [i for i in result.errors() if i.path == "trust.score"]
    decision_issues = [i for i in result.errors() if i.path == "trust.decision"]
    assert score_issues, "trust.score nested object should be rejected"
    assert decision_issues, "trust.decision nested object should be rejected"


def test_string_trust_score_does_not_trip_rule() -> None:
    """Only nested *object* values for trust.score / trust.decision trip
    rule 3. A non-object value (e.g. a string) would fail structural type
    checks but not this specific flat-rule check."""
    env = minimal_v3_envelope()
    env["trust"]["score"] = "stringy"  # type: ignore
    result = validate_envelope(env)
    flat_rule_issues = [i for i in result.errors() if i.path == "trust.score" and "flat" in i.message]
    assert not flat_rule_issues, "trust.score=string should not trip rule 3 (only nested objects do)"
