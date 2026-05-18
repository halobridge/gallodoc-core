"""Tests for `gallodoc.aibi.result_receipts`."""

from __future__ import annotations

from gallodoc.aibi import build_planning_receipt, plan
from gallodoc.aibi.result_receipts import (
    PLANNER_VERSION_DEFAULT,
    QueryResultReceipt,
    _make_receipt_id,
)


def _sample_plan():
    return plan("show invoices linked to John")


def test_planning_receipt_status_is_planned() -> None:
    p = _sample_plan()
    r = build_planning_receipt(p)
    assert r.status == "planned"
    assert r.executed_at is None
    assert r.executed_by_role is None
    assert r.result_count is None
    assert r.policy_outcome_ref is None


def test_planning_receipt_links_to_plan_id() -> None:
    p = _sample_plan()
    r = build_planning_receipt(p)
    assert r.plan_id == p.plan_id


def test_receipt_id_is_deterministic() -> None:
    p = _sample_plan()
    r1 = build_planning_receipt(p)
    r2 = build_planning_receipt(p)
    assert r1.receipt_id == r2.receipt_id


def test_receipt_id_depends_on_planner_version() -> None:
    p = _sample_plan()
    a = _make_receipt_id(p.plan_id, "gallodoc-aibi/3.0.0")
    b = _make_receipt_id(p.plan_id, "gallodoc-aibi/3.1.0")
    assert a != b


def test_receipt_id_format() -> None:
    p = _sample_plan()
    r = build_planning_receipt(p)
    assert r.receipt_id.startswith("receipt_")
    assert len(r.receipt_id) == len("receipt_") + 16


def test_to_dict_documented_keys() -> None:
    p = _sample_plan()
    r = build_planning_receipt(p)
    d = r.to_dict()
    expected = {
        "receipt_id",
        "plan_id",
        "executed_at",
        "executed_by_role",
        "result_count",
        "status",
        "policy_outcome_ref",
        "created_at",
    }
    assert set(d.keys()) == expected


def test_default_planner_version_constant() -> None:
    assert PLANNER_VERSION_DEFAULT == "gallodoc-aibi/3.0.0"
