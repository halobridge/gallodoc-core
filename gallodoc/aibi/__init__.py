"""GalloDoc AI/BI planner — natural-language → QueryPlan.

This package ships a deterministic, template-based planner that emits
`QueryPlan` objects targeting the v2.0 `query_access` (GQL) grammar.
An executor is out of scope for v3.0.

See `docs/specs/gallodoc-core-v3-aibi-planner.md`.
"""

from __future__ import annotations

from gallodoc.aibi.planner import plan
from gallodoc.aibi.query_model import (
    FILTER_OPS,
    SAFE_QUERY_TYPES,
    Filter,
    PolicyCheck,
    QueryPlan,
)
from gallodoc.aibi.result_receipts import (
    QueryResultReceipt,
    build_planning_receipt,
)
from gallodoc.aibi.safe_filters import (
    UnsafePlanError,
    assert_plan_is_safe,
    validate_plan,
)

__all__ = [
    "plan",
    "QueryPlan",
    "Filter",
    "PolicyCheck",
    "SAFE_QUERY_TYPES",
    "FILTER_OPS",
    "validate_plan",
    "assert_plan_is_safe",
    "UnsafePlanError",
    "QueryResultReceipt",
    "build_planning_receipt",
]
