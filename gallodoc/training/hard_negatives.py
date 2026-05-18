"""Deterministic hard-negative generator.

Implements the four strategies in
``docs/specs/gallodoc-core-v3-training-lab.md`` §4. Each strategy emits
synthetic ``TrainingPair`` objects with ``label: "non_match"`` and
``discovered_by: "hard_negative:<strategy>"``.

All strategies are deterministic — same input envelopes produce the
same pairs in the same order — and capped at 10 pairs per group to keep
the pipeline bounded.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Callable

from gallodoc.training.pairs import TrainingPair, _make_pair_id, _now_iso


# Module-level constants used by the customer-name strategy. Substring
# matching on these tokens is a coarse but deterministic proxy for
# "this envelope mentions a customer name shaped like X".
_CUSTOMER_NAME_TOKENS: tuple[str, ...] = (
    "Acme",
    "Globex",
    "Initech",
    "Umbrella",
    "Wayne",
    "Stark",
    "Wonka",
)


STRATEGIES: tuple[str, ...] = (
    "same_org_wrong_person",
    "same_vendor_wrong_invoice",
    "similar_clause_different_obligation",
    "same_customer_name_different_domain",
)

_PER_GROUP_CAP: int = 10


# ---------------------------------------------------------------------------
# Helpers shared across strategies.
# ---------------------------------------------------------------------------


def _gallodoc_id(envelope: dict[str, Any]) -> str | None:
    ident = envelope.get("identity")
    if not isinstance(ident, dict):
        return None
    gid = ident.get("gallodoc_id")
    return gid if isinstance(gid, str) and gid else None


def _source_system(envelope: dict[str, Any]) -> str | None:
    src = envelope.get("source")
    if not isinstance(src, dict):
        return None
    sys_ = src.get("source_system")
    return sys_ if isinstance(sys_, str) and sys_ else None


def _document_type(envelope: dict[str, Any]) -> str:
    ident = envelope.get("identity")
    if not isinstance(ident, dict):
        return ""
    dt = ident.get("document_type")
    return dt if isinstance(dt, str) else ""


def _semantic_roles(envelope: dict[str, Any]) -> frozenset[str]:
    gu = envelope.get("gallounits")
    if not isinstance(gu, dict):
        return frozenset()
    units = gu.get("units") or []
    out: set[str] = set()
    for u in units:
        if isinstance(u, dict):
            role = u.get("semantic_role")
            if isinstance(role, str) and role:
                out.add(role)
    return frozenset(out)


def _claim_field_paths(envelope: dict[str, Any]) -> frozenset[str]:
    tl = envelope.get("truth_ledger")
    if not isinstance(tl, dict):
        return frozenset()
    claims = tl.get("claims") or []
    out: set[str] = set()
    for c in claims:
        if isinstance(c, dict):
            fp = c.get("field_path")
            if isinstance(fp, str) and fp:
                out.add(fp)
    return frozenset(out)


def _vendor_name(envelope: dict[str, Any]) -> str | None:
    """Find the envelope's vendor name via truth_ledger or gallounits."""
    tl = envelope.get("truth_ledger")
    if isinstance(tl, dict):
        for c in tl.get("claims") or []:
            if not isinstance(c, dict):
                continue
            if c.get("field_path") == "vendor_name":
                v = c.get("value")
                if isinstance(v, str) and v:
                    return v
    # Fallback: scan unit content_summary for vendor-shaped strings.
    gu = envelope.get("gallounits")
    if isinstance(gu, dict):
        for u in gu.get("units") or []:
            if not isinstance(u, dict):
                continue
            role = u.get("semantic_role")
            if role == "vendor" or role == "vendor_name":
                cs = u.get("content_summary")
                if isinstance(cs, str) and cs:
                    return cs.strip()
    return None


def _unit_summaries(envelope: dict[str, Any]) -> list[str]:
    gu = envelope.get("gallounits")
    if not isinstance(gu, dict):
        return []
    out: list[str] = []
    for u in gu.get("units") or []:
        if isinstance(u, dict):
            cs = u.get("content_summary")
            if isinstance(cs, str):
                out.append(cs)
    return out


def _customer_tokens_in(envelope: dict[str, Any]) -> frozenset[str]:
    summaries = " ".join(_unit_summaries(envelope))
    hits: set[str] = set()
    for tok in _CUSTOMER_NAME_TOKENS:
        if tok in summaries:
            hits.add(tok)
    return frozenset(hits)


# ---------------------------------------------------------------------------
# Pair construction
# ---------------------------------------------------------------------------


def _make_hard_negative(
    source_ref: str,
    target_ref: str,
    strategy: str,
    now: str,
) -> TrainingPair:
    rel_type = "related_to"
    label = "non_match"
    return TrainingPair(
        pair_id=_make_pair_id(source_ref, target_ref, rel_type, label),
        source_gallodoc_ref=source_ref,
        target_gallodoc_ref=target_ref,
        relationship_type=rel_type,
        semantic_intent=None,
        label=label,
        evidence_refs=[],
        reviewer_decision=None,
        confidence=0.0,
        discovered_by=f"hard_negative:{strategy}",
        created_at=now,
    )


def _ordered_pairs(envs: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return all unordered (env_i, env_j) pairs in stable input order."""
    return list(combinations(envs, 2))


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------


def _strategy_same_org_wrong_person(
    envelopes: list[dict[str, Any]], now: str
) -> list[TrainingPair]:
    """Same source_system, different person/employee envelopes."""
    by_org: dict[str, list[dict[str, Any]]] = {}
    for env in envelopes:
        org = _source_system(env)
        if org is None:
            continue
        dt = _document_type(env).lower()
        if "person" not in dt and "employee" not in dt:
            continue
        by_org.setdefault(org, []).append(env)

    out: list[TrainingPair] = []
    for org, group in by_org.items():
        # Stable order: by gallodoc_id ascending.
        ordered = sorted(group, key=lambda e: _gallodoc_id(e) or "")
        emitted = 0
        for a, b in _ordered_pairs(ordered):
            a_id = _gallodoc_id(a)
            b_id = _gallodoc_id(b)
            if not a_id or not b_id or a_id == b_id:
                continue
            out.append(_make_hard_negative(a_id, b_id, "same_org_wrong_person", now))
            emitted += 1
            if emitted >= _PER_GROUP_CAP:
                break
    return out


def _strategy_same_vendor_wrong_invoice(
    envelopes: list[dict[str, Any]], now: str
) -> list[TrainingPair]:
    """Same vendor, different invoice envelopes."""
    by_vendor: dict[str, list[dict[str, Any]]] = {}
    for env in envelopes:
        if _document_type(env).lower() != "invoice":
            continue
        vendor = _vendor_name(env)
        if vendor is None:
            continue
        by_vendor.setdefault(vendor, []).append(env)

    out: list[TrainingPair] = []
    for vendor, group in by_vendor.items():
        ordered = sorted(group, key=lambda e: _gallodoc_id(e) or "")
        emitted = 0
        for a, b in _ordered_pairs(ordered):
            a_id = _gallodoc_id(a)
            b_id = _gallodoc_id(b)
            if not a_id or not b_id or a_id == b_id:
                continue
            out.append(
                _make_hard_negative(a_id, b_id, "same_vendor_wrong_invoice", now)
            )
            emitted += 1
            if emitted >= _PER_GROUP_CAP:
                break
    return out


def _strategy_similar_clause_different_obligation(
    envelopes: list[dict[str, Any]], now: str
) -> list[TrainingPair]:
    """Shared semantic_role values but disjoint claim field_path sets."""
    # The grouping key is the shared semantic_role value. We iterate over
    # each (a, b) pair and check both conditions.
    ordered = sorted(envelopes, key=lambda e: _gallodoc_id(e) or "")
    # Group emissions by their first-shared-role to enforce the per-group cap.
    by_role_cap: dict[str, int] = {}
    out: list[TrainingPair] = []
    for a, b in _ordered_pairs(ordered):
        a_id = _gallodoc_id(a)
        b_id = _gallodoc_id(b)
        if not a_id or not b_id or a_id == b_id:
            continue
        a_roles = _semantic_roles(a)
        b_roles = _semantic_roles(b)
        shared = a_roles & b_roles
        if not shared:
            continue
        a_paths = _claim_field_paths(a)
        b_paths = _claim_field_paths(b)
        if a_paths & b_paths:
            continue  # claims overlap — not a "different obligation" pair
        # Determine the canonical shared role (lex-smallest) for capping.
        shared_role = sorted(shared)[0]
        if by_role_cap.get(shared_role, 0) >= _PER_GROUP_CAP:
            continue
        by_role_cap[shared_role] = by_role_cap.get(shared_role, 0) + 1
        out.append(
            _make_hard_negative(
                a_id, b_id, "similar_clause_different_obligation", now
            )
        )
    return out


def _strategy_same_customer_name_different_domain(
    envelopes: list[dict[str, Any]], now: str
) -> list[TrainingPair]:
    """Shared customer-name token but different source_system."""
    ordered = sorted(envelopes, key=lambda e: _gallodoc_id(e) or "")
    by_token_cap: dict[str, int] = {}
    out: list[TrainingPair] = []
    for a, b in _ordered_pairs(ordered):
        a_id = _gallodoc_id(a)
        b_id = _gallodoc_id(b)
        if not a_id or not b_id or a_id == b_id:
            continue
        a_tokens = _customer_tokens_in(a)
        b_tokens = _customer_tokens_in(b)
        shared = a_tokens & b_tokens
        if not shared:
            continue
        a_sys = _source_system(a)
        b_sys = _source_system(b)
        if not a_sys or not b_sys or a_sys == b_sys:
            continue
        shared_token = sorted(shared)[0]
        if by_token_cap.get(shared_token, 0) >= _PER_GROUP_CAP:
            continue
        by_token_cap[shared_token] = by_token_cap.get(shared_token, 0) + 1
        out.append(
            _make_hard_negative(
                a_id, b_id, "same_customer_name_different_domain", now
            )
        )
    return out


_STRATEGY_DISPATCH: dict[str, Callable[[list[dict[str, Any]], str], list[TrainingPair]]] = {
    "same_org_wrong_person": _strategy_same_org_wrong_person,
    "same_vendor_wrong_invoice": _strategy_same_vendor_wrong_invoice,
    "similar_clause_different_obligation": _strategy_similar_clause_different_obligation,
    "same_customer_name_different_domain": _strategy_same_customer_name_different_domain,
}


def generate_hard_negatives(
    envelopes: list[dict[str, Any]],
    *,
    strategies: list[str] | None = None,
) -> list[TrainingPair]:
    """Generate synthetic negative pairs from a corpus of v3 envelopes.

    Parameters
    ----------
    envelopes:
        A list of v3 envelopes (already deserialized).
    strategies:
        Optional list of strategy names. Defaults to all four.

    Returns
    -------
    A list of :class:`TrainingPair` objects with ``label: "non_match"``
    and ``discovered_by: "hard_negative:<strategy>"``. Deterministic.
    """
    if strategies is None:
        strategies = list(STRATEGIES)
    now = _now_iso()
    out: list[TrainingPair] = []
    for strat in strategies:
        fn = _STRATEGY_DISPATCH.get(strat)
        if fn is None:
            continue  # unknown strategy — silently skip
        out.extend(fn(list(envelopes), now))
    return out


__all__ = ["STRATEGIES", "generate_hard_negatives"]
