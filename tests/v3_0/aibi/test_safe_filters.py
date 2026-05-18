"""Tests for `gallodoc.aibi.safe_filters`."""

from __future__ import annotations

import pytest

from gallodoc.aibi.query_model import Filter, PolicyCheck, QueryPlan, _now_iso
from gallodoc.aibi.safe_filters import (
    UnsafePlanError,
    assert_plan_is_safe,
    validate_decision_2_flat_trust,
    validate_field_path,
    validate_plan,
)


def _make_minimal_plan(filters: list[Filter] | None = None, user_intent: str = "ok intent") -> QueryPlan:
    return QueryPlan(
        plan_id="plan_test01",
        user_intent_summary=user_intent,
        safe_query_type="relationship_query",
        required_blocks=["relationships"],
        filters=filters or [],
        policy_checks=[PolicyCheck(check="relationship_status", status_in=["confirmed"])],
        expected_output_shape="list[dict]",
        max_results=50,
        created_at="2026-05-17T00:00:00Z",
    )


def test_clean_plan_passes() -> None:
    plan = _make_minimal_plan([Filter(op="eq", field="identity.gallodoc_id", value="doc_001")])
    assert_plan_is_safe(plan)  # does not raise


def test_select_statement_blocked() -> None:
    plan = _make_minimal_plan(
        [Filter(op="eq", field="identity.gallodoc_id", value="SELECT * FROM users")]
    )
    with pytest.raises(UnsafePlanError, match="SQL-shaped pattern"):
        assert_plan_is_safe(plan)


def test_backtick_blocked() -> None:
    plan = _make_minimal_plan([Filter(op="eq", field="identity.gallodoc_id", value="bad`name")])
    with pytest.raises(UnsafePlanError, match="SQL-shaped pattern"):
        assert_plan_is_safe(plan)


def test_semicolon_blocked() -> None:
    plan = _make_minimal_plan([Filter(op="eq", field="identity.gallodoc_id", value="doc;001")])
    with pytest.raises(UnsafePlanError, match="SQL-shaped pattern"):
        assert_plan_is_safe(plan)


def test_sql_line_comment_blocked() -> None:
    plan = _make_minimal_plan([Filter(op="eq", field="identity.gallodoc_id", value="doc--001")])
    with pytest.raises(UnsafePlanError, match="SQL-shaped pattern"):
        assert_plan_is_safe(plan)


def test_sql_block_comment_blocked() -> None:
    plan = _make_minimal_plan([Filter(op="eq", field="identity.gallodoc_id", value="doc/*x*/")])
    with pytest.raises(UnsafePlanError, match="SQL-shaped pattern"):
        assert_plan_is_safe(plan)


def test_insert_keyword_blocked() -> None:
    plan = _make_minimal_plan(user_intent="please INSERT into users")
    with pytest.raises(UnsafePlanError):
        assert_plan_is_safe(plan)


def test_drop_keyword_blocked() -> None:
    plan = _make_minimal_plan(user_intent="DROP table users")
    with pytest.raises(UnsafePlanError):
        assert_plan_is_safe(plan)


def test_flat_trust_components_valid() -> None:
    # Decision 2 — flat trust.components is the supported path.
    validate_field_path("trust.components")
    validate_decision_2_flat_trust("trust.components")
    validate_field_path("trust.decision_gates")
    validate_decision_2_flat_trust("trust.decision_gates")


def test_nested_trust_score_components_rejected() -> None:
    # Decision 2 — nested forbidden.
    with pytest.raises(UnsafePlanError, match="flat \\(Decision 2\\)"):
        validate_decision_2_flat_trust("trust.score.components")


def test_nested_trust_decision_gates_rejected() -> None:
    with pytest.raises(UnsafePlanError, match="flat \\(Decision 2\\)"):
        validate_decision_2_flat_trust("trust.decision.gates")


def test_unknown_top_level_block_rejected() -> None:
    with pytest.raises(UnsafePlanError, match="does not start with an allowed envelope-block prefix"):
        validate_field_path("attacker_block.x")


def test_empty_field_ok() -> None:
    # Some filters (e.g., time_range without explicit field) may omit field.
    validate_field_path("")  # does not raise


def test_validate_plan_runs_all_checks() -> None:
    plan = _make_minimal_plan([Filter(op="eq", field="trust.components", value="x")])
    validate_plan(plan)  # does not raise


def test_validate_plan_rejects_nested_trust() -> None:
    plan = _make_minimal_plan([Filter(op="eq", field="trust.score.components", value="x")])
    with pytest.raises(UnsafePlanError):
        validate_plan(plan)


def test_validate_plan_rejects_unknown_prefix() -> None:
    plan = _make_minimal_plan([Filter(op="eq", field="badblock.x", value="x")])
    with pytest.raises(UnsafePlanError):
        validate_plan(plan)


def test_bare_status_field_ok() -> None:
    # Decision 3 — bare status is a permitted field on a relationship entry.
    validate_field_path("status")
    validate_field_path("discovered_by")
    validate_field_path("confidence")
