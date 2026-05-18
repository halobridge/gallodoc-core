"""Forward-looking receipt scaffold for the NL→GQL planner.

A `QueryResultReceipt` is produced by the planner (status ``"planned"``)
and would later be mutated by a real executor (out of scope for v3.0) to
record the actual execution outcome.

Receipts are part of the audit trail and would persist into
``query_access.query_receipts[]`` once an executor exists.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from gallodoc.aibi.query_model import QueryPlan, _now_iso


PLANNER_VERSION_DEFAULT = "gallodoc-aibi/3.0.0"


@dataclass
class QueryResultReceipt:
    receipt_id: str
    plan_id: str
    executed_at: str | None
    executed_by_role: str | None
    result_count: int | None
    status: str  # "planned" | "executed_success" | "executed_failed" | "policy_blocked"
    policy_outcome_ref: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "plan_id": self.plan_id,
            "executed_at": self.executed_at,
            "executed_by_role": self.executed_by_role,
            "result_count": self.result_count,
            "status": self.status,
            "policy_outcome_ref": self.policy_outcome_ref,
            "created_at": self.created_at,
        }


def _make_receipt_id(plan_id: str, planner_version: str) -> str:
    payload = f"{plan_id}::{planner_version}".encode("utf-8")
    return "receipt_" + hashlib.sha256(payload).hexdigest()[:16]


def build_planning_receipt(
    plan: QueryPlan,
    *,
    planner_version: str = PLANNER_VERSION_DEFAULT,
) -> QueryResultReceipt:
    """Create a 'planned' receipt for the supplied QueryPlan.

    The receipt's executed_* fields are None until a real executor (out
    of scope for v3.0) runs the plan and populates them.
    """
    return QueryResultReceipt(
        receipt_id=_make_receipt_id(plan.plan_id, planner_version),
        plan_id=plan.plan_id,
        executed_at=None,
        executed_by_role=None,
        result_count=None,
        status="planned",
        policy_outcome_ref=None,
        created_at=_now_iso(),
    )


__all__ = [
    "QueryResultReceipt",
    "build_planning_receipt",
    "PLANNER_VERSION_DEFAULT",
]
