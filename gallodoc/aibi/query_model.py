"""Query plan data model — safe primitives only.

A QueryPlan is the output of `gallodoc.aibi.planner.plan(...)`. It targets the
v2.0 query_access (GQL) grammar; an executor is out of scope for v3.0.

No raw SQL. The Filter ops are a closed enum.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


SAFE_QUERY_TYPES: frozenset[str] = frozenset({
    "relationship_query",
    "semantic_similarity_query",
    "operational_timeline_query",
    "evidence_chain_query",
    "trust_query",
})


FILTER_OPS: frozenset[str] = frozenset({
    "eq",
    "in_",
    "has_token",
    "has_relationship",
    "time_range",
    "confidence_at_least",
})


@dataclass
class Filter:
    op: str
    field: str | None = None
    value: Any = None
    values: list[Any] | None = None
    relationship_type: str | None = None
    min_confidence: float | None = None
    from_: str | None = None  # 'from' is a Python reserved word — use trailing underscore
    to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.op not in FILTER_OPS:
            raise ValueError(f"filter op must be in FILTER_OPS, got {self.op!r}")
        out: dict[str, Any] = {"op": self.op}
        if self.field is not None:
            out["field"] = self.field
        if self.value is not None:
            out["value"] = self.value
        if self.values is not None:
            out["values"] = self.values
        if self.relationship_type is not None:
            out["relationship_type"] = self.relationship_type
        if self.min_confidence is not None:
            out["min_confidence"] = self.min_confidence
        if self.from_ is not None:
            out["from"] = self.from_
        if self.to is not None:
            out["to"] = self.to
        return out


@dataclass
class PolicyCheck:
    check: str
    status_in: list[str] | None = None
    scopes_allowed: list[str] | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"check": self.check}
        if self.status_in is not None:
            out["status_in"] = self.status_in
        if self.scopes_allowed is not None:
            out["scopes_allowed"] = self.scopes_allowed
        out.update(self.extras)
        return out


@dataclass
class QueryPlan:
    plan_id: str
    user_intent_summary: str
    safe_query_type: str
    required_blocks: list[str]
    filters: list[Filter]
    policy_checks: list[PolicyCheck]
    expected_output_shape: str
    max_results: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        if self.safe_query_type not in SAFE_QUERY_TYPES:
            raise ValueError(
                f"safe_query_type must be in SAFE_QUERY_TYPES, got {self.safe_query_type!r}"
            )
        return {
            "plan_id": self.plan_id,
            "user_intent_summary": self.user_intent_summary,
            "safe_query_type": self.safe_query_type,
            "required_blocks": self.required_blocks,
            "filters": [f.to_dict() for f in self.filters],
            "policy_checks": [p.to_dict() for p in self.policy_checks],
            "expected_output_shape": self.expected_output_shape,
            "max_results": self.max_results,
            "created_at": self.created_at,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _make_plan_id(user_intent_summary: str, safe_query_type: str) -> str:
    """Deterministic plan_id from intent + type."""
    payload = f"{user_intent_summary}::{safe_query_type}".encode("utf-8")
    return "plan_" + hashlib.sha256(payload).hexdigest()[:16]


__all__ = [
    "SAFE_QUERY_TYPES",
    "FILTER_OPS",
    "Filter",
    "PolicyCheck",
    "QueryPlan",
]
