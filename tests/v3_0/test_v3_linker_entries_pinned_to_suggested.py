"""v3 validator rule 1: linker-discovered relationships gate on a matching
decision record in `relationship_decisions[]` (Decision 3).

Status combinations for a linker-discovered relationship:

* `status="suggested"` without a decision record → valid (the linker just wrote it)
* `status="confirmed"` with a matching `relationship_decisions[]` entry → valid
* `status="rejected"`  with a matching `relationship_decisions[]` entry → valid
* `status="confirmed"|"rejected"` without a decision record → REJECT
* `status="suggested"` with a decision record for this id → REJECT (inconsistent)

`discovered_by` is preserved through the lifecycle so the audit trail
shows machine-proposed + human-confirmed (Decision 3, supersession move
intent).
"""

from __future__ import annotations

import pytest

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


def _envelope_with_relationship(discovered_by: str, status: str) -> dict:
    env = minimal_v3_envelope()
    env["relationships"]["relationships"] = [
        {
            "relationship_id": "rel-001",
            "source_document_ref": "doc-a",
            "target_document_ref": "doc-b",
            "relationship_type": "same_entity_candidate",
            "status": status,
            "discovered_by": discovered_by,
            "confidence": 0.7,
            "created_at": "2026-05-16T00:00:00+00:00",
        }
    ]
    return env


@pytest.mark.parametrize(
    "discovered_by",
    [
        "gallodoc-linker/3.0.0",
        "linker_v3",
        "my-LINKER",
        "deterministic-Linker-v1",
    ],
)
def test_linker_match_rejects_confirmed(discovered_by: str) -> None:
    """status=confirmed without a decision record is rejected."""
    env = _envelope_with_relationship(discovered_by, "confirmed")
    result = validate_envelope(env)
    assert not result.valid, f"{discovered_by!r} with status=confirmed (no decision) should be rejected"
    matching = [
        i
        for i in result.errors()
        if i.path == "relationships.relationships[0].status"
        and "linker" in i.message
        and "relationship_decisions" in i.message
    ]
    assert matching, f"expected linker decision-record issue, got {[(i.path, i.message) for i in result.errors()]}"


@pytest.mark.parametrize(
    "discovered_by",
    [
        "gallodoc-linker/3.0.0",
        "linker_v3",
        "my-LINKER",
    ],
)
def test_linker_match_rejects_rejected(discovered_by: str) -> None:
    env = _envelope_with_relationship(discovered_by, "rejected")
    result = validate_envelope(env)
    assert not result.valid, f"{discovered_by!r} with status=rejected should be rejected"


@pytest.mark.parametrize(
    "discovered_by",
    [
        "gallodoc-linker/3.0.0",
        "linker_v3",
        "my-LINKER",
    ],
)
def test_linker_match_accepts_suggested(discovered_by: str) -> None:
    env = _envelope_with_relationship(discovered_by, "suggested")
    result = validate_envelope(env)
    # No linker-pin issue. (Other structural issues should not appear either,
    # but the test focuses on the linker rule.)
    linker_issues = [i for i in result.issues if "linker" in i.message and "suggested" in i.message]
    assert not linker_issues, "linker entry with status=suggested should not trip the rule"
    assert result.valid, f"linker entry with status=suggested should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_human_review_discovered_by_does_not_match_rule() -> None:
    """`discovered_by: "human_review"` does NOT match /.*linker.*/i — a
    human-confirmed relationship with status=confirmed must pass."""
    env = _envelope_with_relationship("human_review", "confirmed")
    result = validate_envelope(env)
    linker_issues = [i for i in result.issues if "linker" in i.message]
    assert not linker_issues, "human_review entries must not trip the linker rule"
    assert result.valid, f"human_review entry should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_connector_discovered_by_does_not_match_rule() -> None:
    """Connector-emitted relationships with confirmed status are fine —
    only the literal substring 'linker' triggers the rule."""
    env = _envelope_with_relationship("connector:invoice_stub", "confirmed")
    result = validate_envelope(env)
    linker_issues = [i for i in result.issues if "linker" in i.message]
    assert not linker_issues
    assert result.valid


# ---------------------------------------------------------------------------
# Decision 3 lifecycle rule — six explicit status × decision-record cases.
# ---------------------------------------------------------------------------


def _envelope_with_relationship_and_decision(
    discovered_by: str,
    status: str,
    *,
    include_decision: bool,
    decision_verdict: str = "confirmed",
    decision_rel_id: str = "rel-001",
) -> dict:
    """Build an envelope with one linker-discovered relationship and,
    optionally, a matching `relationship_decisions[]` record."""
    env = minimal_v3_envelope()
    env["relationships"]["relationships"] = [
        {
            "relationship_id": "rel-001",
            "source_document_ref": "doc-a",
            "target_document_ref": "doc-b",
            "relationship_type": "same_entity_candidate",
            "status": status,
            "discovered_by": discovered_by,
            "confidence": 0.7,
            "created_at": "2026-05-16T00:00:00+00:00",
        }
    ]
    if include_decision:
        env["relationships"]["relationship_decisions"] = [
            {
                "decision_id": "dec-001",
                "relationship_id": decision_rel_id,
                "verdict": decision_verdict,
                "decided_by": "human_review",
                "decided_at": "2026-05-16T00:01:00+00:00",
                "rationale": "",
            }
        ]
    return env


# Case 1 (valid): status=suggested, no decision record.
def test_suggested_no_decision_validates() -> None:
    env = _envelope_with_relationship_and_decision(
        "gallodoc-linker/3.0.0", "suggested", include_decision=False
    )
    result = validate_envelope(env)
    linker_issues = [i for i in result.errors() if "linker" in i.message]
    assert not linker_issues, (
        f"suggested + no decision should validate, got {[(i.path, i.message) for i in linker_issues]}"
    )
    assert result.valid


# Case 2 (valid): status=confirmed + matching decision.
def test_confirmed_with_decision_validates() -> None:
    env = _envelope_with_relationship_and_decision(
        "gallodoc-linker/3.0.0",
        "confirmed",
        include_decision=True,
        decision_verdict="confirmed",
    )
    result = validate_envelope(env)
    linker_issues = [i for i in result.errors() if "linker" in i.message]
    assert not linker_issues, (
        f"confirmed + matching decision should validate, got {[(i.path, i.message) for i in linker_issues]}"
    )
    assert result.valid


# Case 3 (valid): status=rejected + matching decision.
def test_rejected_with_decision_validates() -> None:
    env = _envelope_with_relationship_and_decision(
        "gallodoc-linker/3.0.0",
        "rejected",
        include_decision=True,
        decision_verdict="rejected",
    )
    result = validate_envelope(env)
    linker_issues = [i for i in result.errors() if "linker" in i.message]
    assert not linker_issues, (
        f"rejected + matching decision should validate, got {[(i.path, i.message) for i in linker_issues]}"
    )
    assert result.valid


# Case 4 (invalid): status=confirmed without a decision record.
def test_confirmed_no_decision_rejects() -> None:
    env = _envelope_with_relationship_and_decision(
        "gallodoc-linker/3.0.0", "confirmed", include_decision=False
    )
    result = validate_envelope(env)
    matching = [
        i
        for i in result.errors()
        if i.path == "relationships.relationships[0].status"
        and "linker" in i.message
        and "relationship_decisions" in i.message
    ]
    assert matching, (
        f"confirmed + no decision should reject with decision-record message, "
        f"got {[(i.path, i.message) for i in result.errors()]}"
    )
    assert not result.valid


# Case 5 (invalid): status=rejected without a decision record.
def test_rejected_no_decision_rejects() -> None:
    env = _envelope_with_relationship_and_decision(
        "gallodoc-linker/3.0.0", "rejected", include_decision=False
    )
    result = validate_envelope(env)
    matching = [
        i
        for i in result.errors()
        if i.path == "relationships.relationships[0].status"
        and "linker" in i.message
        and "relationship_decisions" in i.message
    ]
    assert matching, (
        f"rejected + no decision should reject with decision-record message, "
        f"got {[(i.path, i.message) for i in result.errors()]}"
    )
    assert not result.valid


# Case 6 (invalid): status=suggested but a decision record exists for this id.
def test_suggested_with_decision_rejects_inconsistent() -> None:
    env = _envelope_with_relationship_and_decision(
        "gallodoc-linker/3.0.0",
        "suggested",
        include_decision=True,
        decision_verdict="confirmed",  # contradicts status=suggested
    )
    result = validate_envelope(env)
    matching = [
        i
        for i in result.errors()
        if i.path == "relationships.relationships[0].status"
        and "linker" in i.message
        and "inconsistent" in i.message
    ]
    assert matching, (
        f"suggested + decision should reject as inconsistent, "
        f"got {[(i.path, i.message) for i in result.errors()]}"
    )
    assert not result.valid
