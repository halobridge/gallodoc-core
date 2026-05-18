"""NL → QueryPlan template matcher.

Deterministic, template-based. Each `_plan_*` function returns a
`QueryPlan` if its trigger phrases match the input NL, else `None`.

`plan(nl, envelope)` tries each template in priority order, attaches
mandatory `policy_checks`, and runs `validate_plan` before returning.

No raw SQL. No new query language. The planner targets the existing
v2.0 `query_access` (GQL) grammar.
"""

from __future__ import annotations

import re
from typing import Any

from gallodoc.aibi.query_model import (
    Filter,
    PolicyCheck,
    QueryPlan,
    _make_plan_id,
    _now_iso,
)
from gallodoc.aibi.safe_filters import validate_plan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_MAX_RESULTS = 50


def _normalize(nl: str) -> str:
    return nl.strip().lower()


def _phrase_match(nl_norm: str, phrases: list[str]) -> bool:
    return any(phrase in nl_norm for phrase in phrases)


def _extract_after(nl: str, marker: str) -> str | None:
    """Return the substring after the first occurrence of ``marker`` (case-insensitive)."""
    idx = nl.lower().find(marker.lower())
    if idx < 0:
        return None
    rest = nl[idx + len(marker):].strip(" \t\n.?!,")
    return rest or None


_CROSS_TENANT_PHRASES = ["across tenants", "cross-tenant", "cross tenant", "tenant boundary"]


# Federation scope mapping (matches docs/specs/gallodoc-core-v3-aibi-planner.md §9
# and gallodoc.federation.policy._SCOPE_RESTRICTIVENESS, Decision 4).
#
# The rule: a source envelope with sharing_scope = X permits matching against
# remote envelopes whose sharing_scope is in scopes_allowed[X]. The most-
# restrictive intersection is computed at executor time; the planner only
# records the *set* of remote scopes that could satisfy the source side.
_FEDERATION_SCOPE_MAP: dict[str, list[str]] = {
    "disabled": [],
    "tenant_private": [],
    "fingerprint_only": ["fingerprint_only", "trusted_exchange"],
    "semantic_only": ["semantic_only", "trusted_exchange"],
    "trusted_exchange": ["fingerprint_only", "semantic_only", "trusted_exchange"],
}


def _is_cross_tenant_query(nl: str, envelope: dict[str, Any] | None) -> bool:
    nl_lower = nl.lower()
    if any(p in nl_lower for p in _CROSS_TENANT_PHRASES):
        return True
    if envelope is not None and isinstance(envelope.get("federation"), dict):
        fed = envelope["federation"]
        # treat as cross-tenant if a non-default federation block is present
        if fed and isinstance(fed, dict):
            policy = fed.get("cross_tenant_policy") or {}
            scope = policy.get("sharing_scope")
            if scope and scope != "tenant_private":
                return True
    return False


def _federation_scopes_from_envelope(envelope: dict[str, Any] | None) -> list[str]:
    if envelope is None:
        return ["fingerprint_only", "trusted_exchange"]
    fed = envelope.get("federation") or {}
    policy = fed.get("cross_tenant_policy") or {}
    scope = str(policy.get("sharing_scope", "tenant_private"))
    return list(_FEDERATION_SCOPE_MAP.get(scope, []))


def _relationship_status_from_nl(nl: str) -> list[str]:
    nl_lower = nl.lower()
    statuses: list[str] = []
    # Detect explicit overrides; default is ["confirmed"].
    if "suggested" in nl_lower:
        statuses.append("suggested")
    if "rejected" in nl_lower:
        statuses.append("rejected")
    if "confirmed" in nl_lower and "confirmed" not in statuses:
        statuses.append("confirmed")
    if not statuses:
        statuses = ["confirmed"]
    return statuses


def _attach_mandatory_policy_checks(
    safe_query_type: str,
    nl: str,
    envelope: dict[str, Any] | None,
    existing: list[PolicyCheck],
) -> list[PolicyCheck]:
    out = list(existing)
    if safe_query_type == "relationship_query":
        out.append(
            PolicyCheck(
                check="relationship_status",
                status_in=_relationship_status_from_nl(nl),
            )
        )
    if _is_cross_tenant_query(nl, envelope):
        out.append(
            PolicyCheck(
                check="federation_intersection",
                scopes_allowed=_federation_scopes_from_envelope(envelope),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Template 1 — relationship_query
# ---------------------------------------------------------------------------

_RELATIONSHIP_PHRASES = [
    "linked to",
    "related to",
    "who approves",
    "invoices for",
    "supports",
    "duplicate of",
]


def _plan_relationship_query(nl: str, envelope: dict[str, Any] | None) -> QueryPlan | None:
    nl_norm = _normalize(nl)
    if not _phrase_match(nl_norm, _RELATIONSHIP_PHRASES):
        return None

    summary = nl.strip()
    target: str | None = None
    for marker in ("linked to ", "related to ", "invoices for ", "supports ", "duplicate of "):
        target = _extract_after(nl, marker)
        if target:
            break

    filters: list[Filter] = []
    if target:
        filters.append(
            Filter(
                op="eq",
                field="relationships.relationships[].target_label",
                value=target,
            )
        )
    # If the user said "approves", anchor on relationship_type.
    if "approves" in nl_norm or "approver" in nl_norm:
        filters.append(
            Filter(
                op="has_relationship",
                relationship_type="invoice_to_employee_approver",
                min_confidence=0.6,
            )
        )
    # Salesforce account / CRM account → same_customer relationship.
    if "salesforce account" in nl_norm or "crm account" in nl_norm:
        filters.append(
            Filter(
                op="has_relationship",
                relationship_type="same_customer",
                min_confidence=0.6,
            )
        )

    return QueryPlan(
        plan_id=_make_plan_id(summary, "relationship_query"),
        user_intent_summary=summary,
        safe_query_type="relationship_query",
        required_blocks=["relationships", "identity"],
        filters=filters,
        policy_checks=[],  # populated by _attach_mandatory_policy_checks
        expected_output_shape="list[dict]",
        max_results=_DEFAULT_MAX_RESULTS,
        created_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Template 2 — semantic_similarity_query
# ---------------------------------------------------------------------------

_SIMILARITY_PHRASES = [
    "similar to",
    "near this",
    "documents like",
]


def _plan_semantic_similarity_query(nl: str, envelope: dict[str, Any] | None) -> QueryPlan | None:
    nl_norm = _normalize(nl)
    if not _phrase_match(nl_norm, _SIMILARITY_PHRASES):
        return None

    summary = nl.strip()
    target: str | None = None
    for marker in ("similar to ", "near this ", "documents like "):
        target = _extract_after(nl, marker)
        if target:
            break

    filters: list[Filter] = []
    if target:
        filters.append(
            Filter(
                op="has_token",
                field="gallounits.units[].semantic_intent",
                value=target,
            )
        )
    filters.append(
        Filter(op="confidence_at_least", field="confidence", value=0.5)
    )

    return QueryPlan(
        plan_id=_make_plan_id(summary, "semantic_similarity_query"),
        user_intent_summary=summary,
        safe_query_type="semantic_similarity_query",
        required_blocks=["gallounits", "vector_context"],
        filters=filters,
        policy_checks=[],
        expected_output_shape="list[dict]",
        max_results=_DEFAULT_MAX_RESULTS,
        created_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Template 3 — operational_timeline_query
# ---------------------------------------------------------------------------

_TIMELINE_PHRASES = [
    "events in ",
    "decisions in ",
    "what happened to ",
    "timeline for ",
]

_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


def _extract_time_range(nl: str) -> tuple[str | None, str | None]:
    """Try to extract an ISO-8601 ``from`` / ``to`` window from the NL.

    Recognizes ``<month> <year>`` (e.g. "May 2026") and explicit ISO timestamps.
    """
    nl_lower = nl.lower()
    # month + year
    m = re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b\s*(\d{4})", nl_lower)
    if m:
        month = _MONTHS[m.group(1)]
        year = m.group(2)
        # last day of month — approximate to 28 for safety; executor refines.
        last_day = {
            "01": "31", "02": "28", "03": "31", "04": "30", "05": "31",
            "06": "30", "07": "31", "08": "31", "09": "30", "10": "31",
            "11": "30", "12": "31",
        }[month]
        return (
            f"{year}-{month}-01T00:00:00Z",
            f"{year}-{month}-{last_day}T23:59:59Z",
        )
    return (None, None)


def _plan_operational_timeline_query(nl: str, envelope: dict[str, Any] | None) -> QueryPlan | None:
    nl_norm = _normalize(nl)
    if not _phrase_match(nl_norm, _TIMELINE_PHRASES):
        return None

    summary = nl.strip()
    filters: list[Filter] = []
    t_from, t_to = _extract_time_range(nl)
    if t_from and t_to:
        filters.append(Filter(op="time_range", field="created_at", from_=t_from, to=t_to))

    # If "for vendor X" appears, capture the vendor as an eq filter on activity.
    m = re.search(r"for vendor ([A-Za-z0-9_-]+)", nl, re.IGNORECASE)
    if m:
        filters.append(
            Filter(
                op="eq",
                field="activity.actors[].name",
                value=m.group(1),
            )
        )

    return QueryPlan(
        plan_id=_make_plan_id(summary, "operational_timeline_query"),
        user_intent_summary=summary,
        safe_query_type="operational_timeline_query",
        required_blocks=["lifecycle", "activity"],
        filters=filters,
        policy_checks=[],
        expected_output_shape="list[dict]",
        max_results=_DEFAULT_MAX_RESULTS,
        created_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Template 4 — evidence_chain_query
# ---------------------------------------------------------------------------

_EVIDENCE_PHRASES = [
    "trace evidence for",
    "evidence for trust score",
    "where did ",
]


def _plan_evidence_chain_query(nl: str, envelope: dict[str, Any] | None) -> QueryPlan | None:
    nl_norm = _normalize(nl)
    if not _phrase_match(nl_norm, _EVIDENCE_PHRASES):
        return None

    summary = nl.strip()
    filters: list[Filter] = []

    # If the NL mentions a doc_xxx or specific gallodoc_id, anchor on identity.
    m = re.search(r"\b(doc[_-][A-Za-z0-9_-]+)\b", nl)
    if m:
        filters.append(
            Filter(op="eq", field="identity.gallodoc_id", value=m.group(1))
        )

    # If the NL mentions trust score, anchor evidence on trust.components.
    if "trust score" in nl_norm:
        filters.append(
            Filter(op="confidence_at_least", field="trust.components", value=0.0)
        )

    return QueryPlan(
        plan_id=_make_plan_id(summary, "evidence_chain_query"),
        user_intent_summary=summary,
        safe_query_type="evidence_chain_query",
        required_blocks=["evidence", "truth_ledger", "trust"],
        filters=filters,
        policy_checks=[],
        expected_output_shape="list[dict]",
        max_results=_DEFAULT_MAX_RESULTS,
        created_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Template 5 — trust_query
# ---------------------------------------------------------------------------

_TRUST_PHRASES = [
    "certified under",
    "trust at least",
    "high-confidence envelopes",
    "high confidence envelopes",
]


def _plan_trust_query(nl: str, envelope: dict[str, Any] | None) -> QueryPlan | None:
    nl_norm = _normalize(nl)
    if not _phrase_match(nl_norm, _TRUST_PHRASES):
        return None

    summary = nl.strip()
    filters: list[Filter] = []

    # "certified under policy v2.1" → eq on trust.decision_gates.policy_ref.
    m = re.search(r"certified under (?:policy )?([A-Za-z0-9._-]+)", nl, re.IGNORECASE)
    if m:
        filters.append(
            Filter(
                op="eq",
                field="trust.decision_gates[].policy_ref",
                value=m.group(1),
            )
        )

    # "trust at least 0.7" → confidence_at_least on trust.components.
    m = re.search(r"trust at least\s+([0-9.]+)", nl, re.IGNORECASE)
    if m:
        try:
            threshold = float(m.group(1))
            filters.append(
                Filter(op="confidence_at_least", field="trust.components", value=threshold)
            )
        except ValueError:
            pass

    if "high-confidence" in nl_norm or "high confidence" in nl_norm:
        filters.append(
            Filter(op="confidence_at_least", field="trust.components", value=0.8)
        )

    return QueryPlan(
        plan_id=_make_plan_id(summary, "trust_query"),
        user_intent_summary=summary,
        safe_query_type="trust_query",
        required_blocks=["trust", "certification"],
        filters=filters,
        policy_checks=[],
        expected_output_shape="list[dict]",
        max_results=_DEFAULT_MAX_RESULTS,
        created_at=_now_iso(),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

# Priority order: evidence_chain and trust_query are checked before
# relationship_query so the keyword "supports" inside "trust score"
# evidence-tracing queries doesn't mis-route to relationship_query.
_TEMPLATES = (
    _plan_evidence_chain_query,
    _plan_trust_query,
    _plan_semantic_similarity_query,
    _plan_operational_timeline_query,
    _plan_relationship_query,
)


def plan(nl: str, envelope: dict[str, Any] | None = None) -> QueryPlan:
    """Match the NL string against the 5 templates and return a QueryPlan.

    Raises ``ValueError`` if no template matches, or
    ``UnsafePlanError`` if the produced plan fails the safety / field-path
    validations.
    """
    if not isinstance(nl, str) or not nl.strip():
        raise ValueError("nl must be a non-empty string")

    matched: QueryPlan | None = None
    for tpl in _TEMPLATES:
        matched = tpl(nl, envelope)
        if matched is not None:
            break

    if matched is None:
        raise ValueError(
            "no template matched the natural-language input — try one of the 5 "
            "supported query types: relationship_query, semantic_similarity_query, "
            "operational_timeline_query, evidence_chain_query, trust_query"
        )

    # Attach mandatory policy_checks now that we know the type.
    matched.policy_checks = _attach_mandatory_policy_checks(
        matched.safe_query_type,
        nl,
        envelope,
        matched.policy_checks,
    )

    validate_plan(matched)  # raises UnsafePlanError on regression
    return matched


__all__ = ["plan"]
