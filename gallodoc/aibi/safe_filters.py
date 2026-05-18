"""Safe-primitive guard and field-path validator for QueryPlan filters.

The no-raw-SQL invariant is enforced by scanning every field value (including
filter values and policy_check extras) for SQL-shaped patterns.
"""

from __future__ import annotations

import re
from typing import Any

from gallodoc.aibi.query_model import QueryPlan


_SQL_FORBIDDEN_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|UNION)\b", re.IGNORECASE),
    re.compile(r";"),
    re.compile(r"`"),
    re.compile(r"--"),    # SQL comment
    re.compile(r"/\*"),   # SQL block comment
]


class UnsafePlanError(ValueError):
    """Raised when a QueryPlan contains raw SQL or other unsafe patterns."""


def assert_plan_is_safe(plan: QueryPlan) -> None:
    """Scan every string in the plan for SQL-shaped patterns. Raise if found."""
    leaks: list[str] = []

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}".lstrip("."))
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            for pat in _SQL_FORBIDDEN_PATTERNS:
                if pat.search(node):
                    leaks.append(
                        f"{path}: SQL-shaped pattern in {node!r} (matched {pat.pattern!r})"
                    )

    walk(plan.to_dict())
    if leaks:
        raise UnsafePlanError(
            f"plan contains unsafe SQL-shaped patterns ({len(leaks)} issue(s)):\n  - "
            + "\n  - ".join(leaks)
        )


# Allowed field-path prefixes for filter.field — anchors filters to known
# envelope blocks. Anything outside this set is rejected.
ALLOWED_FIELD_PREFIXES: frozenset[str] = frozenset({
    "identity.",
    "source.",
    "purpose.",
    "lifecycle.",
    "activity.",
    "relationships.",
    "evidence.",
    "validations.",
    "security.",
    "exports.",
    "extensions.",
    "ai_usage.",
    "gallounits.",
    "certification.",
    "gstp.",
    "truth_ledger.",
    "trust.",                       # Decision 2 — flat trust
    "federation.",                  # Decision 4
    "policy_governance.",
    "access_control.",
    "human_review.",
    "workflow_execution.",
    "vector_context.",
    "temporal_versions.",
    "compute_trace.",
    "artifact_bom.",
    "query_access.",
    "status",                       # Decision 3 — bare status field allowed on a relationship
    "discovered_by",
    "confidence",
    "created_at",
    "decided_at",
    # the bare relationship-entry fields can appear without the relationships. prefix
})


def validate_field_path(field: str) -> None:
    """Reject fields not starting with an allowed prefix."""
    if not field:
        return  # ok — some filters (e.g., time_range without explicit field) may omit
    for prefix in ALLOWED_FIELD_PREFIXES:
        if field == prefix.rstrip(".") or field.startswith(prefix):
            return
    raise UnsafePlanError(
        f"filter.field {field!r} does not start with an allowed envelope-block prefix"
    )


# Reject nested trust.score.* and trust.decision.* per Decision 2.
_NESTED_TRUST_PATTERNS = [
    re.compile(r"^trust\.score\.[A-Za-z_]"),
    re.compile(r"^trust\.decision\.[A-Za-z_]"),
]


def validate_decision_2_flat_trust(field: str) -> None:
    for pat in _NESTED_TRUST_PATTERNS:
        if pat.match(field):
            raise UnsafePlanError(
                f"filter.field {field!r} uses nested trust.score.* / trust.decision.* — "
                f"v3 trust block is flat (Decision 2)"
            )


def validate_plan(plan: QueryPlan) -> None:
    """Run the safety + field-path checks together."""
    assert_plan_is_safe(plan)
    for f in plan.filters:
        if f.field:
            validate_field_path(f.field)
            validate_decision_2_flat_trust(f.field)


__all__ = [
    "UnsafePlanError",
    "assert_plan_is_safe",
    "validate_field_path",
    "validate_decision_2_flat_trust",
    "validate_plan",
    "ALLOWED_FIELD_PREFIXES",
]
