"""Tests for `gallodoc.aibi.query_model`."""

from __future__ import annotations

import pytest

from gallodoc.aibi.query_model import (
    FILTER_OPS,
    SAFE_QUERY_TYPES,
    Filter,
    PolicyCheck,
    QueryPlan,
    _make_plan_id,
    _now_iso,
)


def test_safe_query_types_has_exactly_five() -> None:
    assert len(SAFE_QUERY_TYPES) == 5
    assert SAFE_QUERY_TYPES == frozenset({
        "relationship_query",
        "semantic_similarity_query",
        "operational_timeline_query",
        "evidence_chain_query",
        "trust_query",
    })


def test_filter_ops_has_exactly_six() -> None:
    assert len(FILTER_OPS) == 6
    assert FILTER_OPS == frozenset({
        "eq",
        "in_",
        "has_token",
        "has_relationship",
        "time_range",
        "confidence_at_least",
    })


def test_filter_to_dict_raises_on_unknown_op() -> None:
    f = Filter(op="not_a_real_op", field="x", value="y")
    with pytest.raises(ValueError, match="filter op must be in FILTER_OPS"):
        f.to_dict()


def test_filter_to_dict_renames_from_underscore() -> None:
    f = Filter(op="time_range", from_="2026-01-01T00:00:00Z", to="2026-12-31T23:59:59Z")
    out = f.to_dict()
    assert "from" in out
    assert "from_" not in out
    assert out["from"] == "2026-01-01T00:00:00Z"
    assert out["to"] == "2026-12-31T23:59:59Z"


def test_filter_to_dict_serializes_eq() -> None:
    f = Filter(op="eq", field="identity.gallodoc_id", value="doc_001")
    out = f.to_dict()
    assert out == {"op": "eq", "field": "identity.gallodoc_id", "value": "doc_001"}


def test_filter_to_dict_serializes_in_() -> None:
    f = Filter(op="in_", field="status", values=["confirmed", "suggested"])
    out = f.to_dict()
    assert out["op"] == "in_"
    assert out["values"] == ["confirmed", "suggested"]


def test_filter_to_dict_serializes_has_relationship() -> None:
    f = Filter(op="has_relationship", relationship_type="same_customer", min_confidence=0.7)
    out = f.to_dict()
    assert out["op"] == "has_relationship"
    assert out["relationship_type"] == "same_customer"
    assert out["min_confidence"] == 0.7


def test_policy_check_to_dict_basic() -> None:
    pc = PolicyCheck(check="relationship_status", status_in=["confirmed"])
    out = pc.to_dict()
    assert out == {"check": "relationship_status", "status_in": ["confirmed"]}


def test_policy_check_to_dict_federation() -> None:
    pc = PolicyCheck(
        check="federation_intersection",
        scopes_allowed=["fingerprint_only", "trusted_exchange"],
    )
    out = pc.to_dict()
    assert out["check"] == "federation_intersection"
    assert out["scopes_allowed"] == ["fingerprint_only", "trusted_exchange"]


def test_query_plan_to_dict_raises_on_unknown_safe_query_type() -> None:
    p = QueryPlan(
        plan_id="plan_abc",
        user_intent_summary="x",
        safe_query_type="not_in_enum",
        required_blocks=["trust"],
        filters=[],
        policy_checks=[],
        expected_output_shape="list[dict]",
        max_results=10,
        created_at=_now_iso(),
    )
    with pytest.raises(ValueError, match="safe_query_type must be in SAFE_QUERY_TYPES"):
        p.to_dict()


def test_query_plan_to_dict_documented_keys() -> None:
    p = QueryPlan(
        plan_id="plan_abc",
        user_intent_summary="show trust scores",
        safe_query_type="trust_query",
        required_blocks=["trust"],
        filters=[Filter(op="confidence_at_least", field="trust.components", value=0.7)],
        policy_checks=[],
        expected_output_shape="list[dict]",
        max_results=50,
        created_at="2026-05-17T00:00:00Z",
    )
    out = p.to_dict()
    expected_keys = {
        "plan_id",
        "user_intent_summary",
        "safe_query_type",
        "required_blocks",
        "filters",
        "policy_checks",
        "expected_output_shape",
        "max_results",
        "created_at",
    }
    assert set(out.keys()) == expected_keys
    assert len(expected_keys) == 9


def test_make_plan_id_is_deterministic() -> None:
    a = _make_plan_id("show invoices for vendor X", "relationship_query")
    b = _make_plan_id("show invoices for vendor X", "relationship_query")
    assert a == b
    assert a.startswith("plan_")
    assert len(a) == len("plan_") + 16


def test_make_plan_id_changes_with_input() -> None:
    a = _make_plan_id("show invoices for vendor X", "relationship_query")
    b = _make_plan_id("show invoices for vendor Y", "relationship_query")
    assert a != b
    c = _make_plan_id("show invoices for vendor X", "trust_query")
    assert a != c
