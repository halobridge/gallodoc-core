"""Tests for `gallodoc.aibi.planner.plan(...)` — NL → QueryPlan."""

from __future__ import annotations

import pytest

from gallodoc.aibi import plan, validate_plan
from gallodoc.aibi.query_model import SAFE_QUERY_TYPES


# ---------------------------------------------------------------------------
# Each safe_query_type matches at least one representative NL string
# ---------------------------------------------------------------------------

def test_relationship_query_matches() -> None:
    p = plan("show invoices linked to John")
    assert p.safe_query_type == "relationship_query"


def test_semantic_similarity_query_matches() -> None:
    p = plan("find documents similar to this contract")
    assert p.safe_query_type == "semantic_similarity_query"


def test_operational_timeline_query_matches() -> None:
    p = plan("show all decisions in May 2026 for vendor X")
    assert p.safe_query_type == "operational_timeline_query"


def test_evidence_chain_query_matches() -> None:
    p = plan("trace evidence for trust score on doc_001")
    assert p.safe_query_type == "evidence_chain_query"


def test_trust_query_matches() -> None:
    p = plan("show envelopes certified under policy v2.1")
    assert p.safe_query_type == "trust_query"


# ---------------------------------------------------------------------------
# Mandatory policy_checks
# ---------------------------------------------------------------------------

def test_relationship_plan_has_relationship_status_check_default_confirmed() -> None:
    p = plan("show invoices linked to John")
    checks = [c.to_dict() for c in p.policy_checks]
    assert any(c["check"] == "relationship_status" for c in checks)
    matching = [c for c in checks if c["check"] == "relationship_status"]
    assert matching[0]["status_in"] == ["confirmed"]


def test_relationship_plan_with_suggested_overrides_status() -> None:
    p = plan("show suggested invoices linked to John")
    matching = [c.to_dict() for c in p.policy_checks if c.check == "relationship_status"]
    assert matching[0]["status_in"] == ["suggested"]


def test_relationship_plan_with_rejected_overrides_status() -> None:
    p = plan("show rejected items linked to John")
    matching = [c.to_dict() for c in p.policy_checks if c.check == "relationship_status"]
    assert matching[0]["status_in"] == ["rejected"]


# ---------------------------------------------------------------------------
# Decision 2 — flat trust paths
# ---------------------------------------------------------------------------

def test_trust_plan_uses_flat_trust_paths() -> None:
    p = plan("show envelopes with trust at least 0.7")
    out = p.to_dict()
    fields = [f.get("field", "") for f in out["filters"]]
    assert any(field == "trust.components" for field in fields)
    # No nested trust paths
    for f in fields:
        assert not f.startswith("trust.score.")
        assert not f.startswith("trust.decision.")


def test_evidence_plan_uses_flat_trust_paths() -> None:
    p = plan("trace evidence for trust score on doc_001")
    out = p.to_dict()
    for f in out["filters"]:
        field = f.get("field", "")
        assert not field.startswith("trust.score.")
        assert not field.startswith("trust.decision.")


# ---------------------------------------------------------------------------
# Unsupported NL → ValueError
# ---------------------------------------------------------------------------

def test_unsupported_nl_raises() -> None:
    with pytest.raises(ValueError, match="no template matched"):
        plan("the quick brown fox jumps over the lazy dog")


def test_empty_nl_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        plan("")


def test_whitespace_only_nl_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        plan("   \t\n   ")


# ---------------------------------------------------------------------------
# All plans pass validate_plan automatically (planner runs it internally)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nl,expected_type", [
    ("show invoices linked to John", "relationship_query"),
    ("find documents similar to this contract", "semantic_similarity_query"),
    ("show events in May 2026 for vendor X", "operational_timeline_query"),
    ("trace evidence for doc_001", "evidence_chain_query"),
    ("show envelopes certified under policy v2.1", "trust_query"),
])
def test_all_plans_validate(nl: str, expected_type: str) -> None:
    p = plan(nl)
    assert p.safe_query_type == expected_type
    # validate_plan should not raise — planner already ran it but verify externally too.
    validate_plan(p)


# ---------------------------------------------------------------------------
# Deterministic plan_id
# ---------------------------------------------------------------------------

def test_plan_id_deterministic_same_input() -> None:
    a = plan("show invoices linked to John")
    b = plan("show invoices linked to John")
    assert a.plan_id == b.plan_id


def test_plan_id_differs_on_different_input() -> None:
    a = plan("show invoices linked to John")
    b = plan("show invoices linked to Jane")
    assert a.plan_id != b.plan_id


# ---------------------------------------------------------------------------
# Safe-query-type closed enum
# ---------------------------------------------------------------------------

def test_every_template_type_is_in_safe_query_types() -> None:
    samples = [
        "show invoices linked to John",
        "find documents similar to this contract",
        "show decisions in May 2026 for vendor X",
        "trace evidence for doc_001",
        "show envelopes certified under policy v2.1",
    ]
    seen = set()
    for nl in samples:
        p = plan(nl)
        seen.add(p.safe_query_type)
        assert p.safe_query_type in SAFE_QUERY_TYPES
    assert len(seen) == 5
