"""Federation policy intersection — most-restrictive-wins logic.

Two envelopes A and B each carry a ``federation.cross_tenant_policy``.
The effective policy for a cross-tenant match between them is the
intersection of A's and B's policies, computed per the rules in
``docs/specs/gallodoc-core-v3-federation.md §6``:

- ``allowed`` — boolean AND
- ``sharing_scope`` — more restrictive of the two (lower index in
  ``_SCOPE_RESTRICTIVENESS``)
- ``raw_data_visible`` — boolean AND
- ``fingerprint_sharing_allowed`` — boolean AND
- ``embedding_sharing_allowed`` — boolean AND
- ``requires_review`` — boolean OR (if either side wants review, the
  candidate is flagged)
- ``permitted_relationship_types`` — set intersection (with empty meaning
  "no restriction")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Scope ordering by restrictiveness (low index = most restrictive).
# Decision 4 / Codex 08 — federation spec §4.
_SCOPE_RESTRICTIVENESS: list[str] = [
    "disabled",          # most restrictive (no match ever)
    "tenant_private",    # no cross-tenant match
    "fingerprint_only",  # hash-based signals only
    "semantic_only",     # embedding-profile signals only
    "trusted_exchange",  # least restrictive (all signals)
]


@dataclass
class CrossTenantPolicy:
    """A tenant's cross-tenant matching policy.

    Defaults are intentionally restrictive: instantiating without arguments
    yields ``tenant_private``, ``allowed=False``, ``requires_review=True``,
    no relationship-type allowlist — a safe no-op for envelopes that lack
    a ``federation`` block entirely.
    """

    allowed: bool = False
    sharing_scope: str = "tenant_private"
    raw_data_visible: bool = False
    fingerprint_sharing_allowed: bool = False
    embedding_sharing_allowed: bool = False
    requires_review: bool = True
    permitted_relationship_types: list[str] = field(default_factory=list)

    @classmethod
    def from_envelope(cls, envelope: dict[str, Any]) -> CrossTenantPolicy:
        """Extract policy from ``envelope.federation.cross_tenant_policy``.

        Returns a default (``tenant_private`` + denied) policy if the
        federation block or the cross_tenant_policy sub-block is absent.
        """
        fed = envelope.get("federation")
        if not isinstance(fed, dict):
            return cls()
        p = fed.get("cross_tenant_policy")
        if not isinstance(p, dict):
            return cls()
        return cls(
            allowed=bool(p.get("allowed", False)),
            sharing_scope=str(p.get("sharing_scope", "tenant_private")),
            raw_data_visible=bool(p.get("raw_data_visible", False)),
            fingerprint_sharing_allowed=bool(p.get("fingerprint_sharing_allowed", False)),
            embedding_sharing_allowed=bool(p.get("embedding_sharing_allowed", False)),
            requires_review=bool(p.get("requires_review", True)),
            permitted_relationship_types=list(p.get("permitted_relationship_types", [])),
        )


def intersect(a: CrossTenantPolicy, b: CrossTenantPolicy) -> CrossTenantPolicy:
    """Most-restrictive-wins intersection of two cross-tenant policies."""
    # allowed: AND
    allowed = a.allowed and b.allowed
    # sharing_scope: pick the more restrictive (lower index)
    try:
        idx_a = _SCOPE_RESTRICTIVENESS.index(a.sharing_scope)
    except ValueError:
        idx_a = 0  # unknown scope → treat as most restrictive
    try:
        idx_b = _SCOPE_RESTRICTIVENESS.index(b.sharing_scope)
    except ValueError:
        idx_b = 0
    scope = _SCOPE_RESTRICTIVENESS[min(idx_a, idx_b)]
    # raw_data_visible: AND (both must allow; v3.0 always false in receipts)
    raw_visible = a.raw_data_visible and b.raw_data_visible
    # fingerprint / embedding sharing: AND (both must allow)
    fp_share = a.fingerprint_sharing_allowed and b.fingerprint_sharing_allowed
    emb_share = a.embedding_sharing_allowed and b.embedding_sharing_allowed
    # requires_review: OR (if either side requires review, candidate requires it)
    review = a.requires_review or b.requires_review
    # permitted_relationship_types: set intersection (empty = no restriction)
    if not a.permitted_relationship_types and not b.permitted_relationship_types:
        rel_types: list[str] = []  # both empty → no restriction
    elif not a.permitted_relationship_types:
        rel_types = list(b.permitted_relationship_types)
    elif not b.permitted_relationship_types:
        rel_types = list(a.permitted_relationship_types)
    else:
        rel_types = sorted(
            set(a.permitted_relationship_types) & set(b.permitted_relationship_types)
        )
    return CrossTenantPolicy(
        allowed=allowed,
        sharing_scope=scope,
        raw_data_visible=raw_visible,
        fingerprint_sharing_allowed=fp_share,
        embedding_sharing_allowed=emb_share,
        requires_review=review,
        permitted_relationship_types=rel_types,
    )


def is_cross_tenant_match_permitted(policy: CrossTenantPolicy) -> bool:
    """True iff a cross-tenant candidate can be produced under this policy.

    Returns ``False`` when the policy is not ``allowed``, or when
    ``sharing_scope`` is ``disabled`` or ``tenant_private``.
    """
    if not policy.allowed:
        return False
    if policy.sharing_scope in ("disabled", "tenant_private"):
        return False
    return True


__all__ = [
    "CrossTenantPolicy",
    "intersect",
    "is_cross_tenant_match_permitted",
]
