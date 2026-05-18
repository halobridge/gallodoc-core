"""Codex 08 — federation policy intersection (most-restrictive wins)."""

from __future__ import annotations

from gallodoc.federation.policy import (
    CrossTenantPolicy,
    intersect,
    is_cross_tenant_match_permitted,
)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_default_policy_is_tenant_private_and_not_allowed() -> None:
    p = CrossTenantPolicy()
    assert p.allowed is False
    assert p.sharing_scope == "tenant_private"
    assert p.raw_data_visible is False
    assert p.fingerprint_sharing_allowed is False
    assert p.embedding_sharing_allowed is False
    assert p.requires_review is True
    assert p.permitted_relationship_types == []


# ---------------------------------------------------------------------------
# from_envelope
# ---------------------------------------------------------------------------


def test_from_envelope_no_federation_block_returns_default() -> None:
    p = CrossTenantPolicy.from_envelope({})
    assert p == CrossTenantPolicy()


def test_from_envelope_no_cross_tenant_policy_returns_default() -> None:
    p = CrossTenantPolicy.from_envelope({"federation": {}})
    assert p == CrossTenantPolicy()


def test_from_envelope_reads_each_field() -> None:
    env = {
        "federation": {
            "cross_tenant_policy": {
                "allowed": True,
                "sharing_scope": "trusted_exchange",
                "raw_data_visible": False,
                "fingerprint_sharing_allowed": True,
                "embedding_sharing_allowed": True,
                "requires_review": False,
                "permitted_relationship_types": ["same_customer", "duplicate_of"],
            }
        }
    }
    p = CrossTenantPolicy.from_envelope(env)
    assert p.allowed is True
    assert p.sharing_scope == "trusted_exchange"
    assert p.raw_data_visible is False
    assert p.fingerprint_sharing_allowed is True
    assert p.embedding_sharing_allowed is True
    assert p.requires_review is False
    assert p.permitted_relationship_types == ["same_customer", "duplicate_of"]


def test_from_envelope_defaults_when_fields_missing() -> None:
    """Missing inner fields default to safe (restrictive) values."""
    env = {"federation": {"cross_tenant_policy": {"allowed": True}}}
    p = CrossTenantPolicy.from_envelope(env)
    assert p.allowed is True
    # Other fields take dataclass defaults
    assert p.sharing_scope == "tenant_private"
    assert p.requires_review is True
    assert p.fingerprint_sharing_allowed is False
    assert p.permitted_relationship_types == []


# ---------------------------------------------------------------------------
# intersect — sharing_scope (most restrictive)
# ---------------------------------------------------------------------------


def _allowed_policy(scope: str, **kwargs: object) -> CrossTenantPolicy:
    kw: dict[str, object] = {"allowed": True, "sharing_scope": scope}
    kw.update(kwargs)
    return CrossTenantPolicy(**kw)  # type: ignore[arg-type]


def test_intersect_trusted_exchange_and_fingerprint_only_is_fingerprint_only() -> None:
    a = _allowed_policy("trusted_exchange")
    b = _allowed_policy("fingerprint_only")
    result = intersect(a, b)
    assert result.sharing_scope == "fingerprint_only"


def test_intersect_disabled_and_trusted_exchange_is_disabled() -> None:
    a = _allowed_policy("disabled")
    b = _allowed_policy("trusted_exchange")
    result = intersect(a, b)
    assert result.sharing_scope == "disabled"


def test_intersect_semantic_only_and_fingerprint_only_is_fingerprint_only() -> None:
    """fingerprint_only is more restrictive than semantic_only."""
    a = _allowed_policy("semantic_only")
    b = _allowed_policy("fingerprint_only")
    result = intersect(a, b)
    assert result.sharing_scope == "fingerprint_only"


def test_intersect_unknown_scope_treated_as_most_restrictive() -> None:
    """Unknown scope value falls into the disabled slot (index 0)."""
    a = _allowed_policy("wonky_value")
    b = _allowed_policy("trusted_exchange")
    result = intersect(a, b)
    assert result.sharing_scope == "disabled"  # unknown → most restrictive


# ---------------------------------------------------------------------------
# intersect — booleans
# ---------------------------------------------------------------------------


def test_intersect_allowed_is_and() -> None:
    assert intersect(
        _allowed_policy("trusted_exchange"),
        CrossTenantPolicy(allowed=False, sharing_scope="trusted_exchange"),
    ).allowed is False
    assert intersect(
        _allowed_policy("trusted_exchange"),
        _allowed_policy("trusted_exchange"),
    ).allowed is True


def test_intersect_requires_review_is_or() -> None:
    a = _allowed_policy("trusted_exchange", requires_review=True)
    b = _allowed_policy("trusted_exchange", requires_review=False)
    assert intersect(a, b).requires_review is True
    # Both false → false
    c = _allowed_policy("trusted_exchange", requires_review=False)
    d = _allowed_policy("trusted_exchange", requires_review=False)
    assert intersect(c, d).requires_review is False


def test_intersect_fingerprint_sharing_is_and() -> None:
    a = _allowed_policy("fingerprint_only", fingerprint_sharing_allowed=True)
    b = _allowed_policy("fingerprint_only", fingerprint_sharing_allowed=False)
    assert intersect(a, b).fingerprint_sharing_allowed is False


def test_intersect_embedding_sharing_is_and() -> None:
    a = _allowed_policy("trusted_exchange", embedding_sharing_allowed=True)
    b = _allowed_policy("trusted_exchange", embedding_sharing_allowed=False)
    assert intersect(a, b).embedding_sharing_allowed is False


def test_intersect_raw_data_visible_is_and() -> None:
    a = _allowed_policy("trusted_exchange", raw_data_visible=False)
    b = _allowed_policy("trusted_exchange", raw_data_visible=False)
    assert intersect(a, b).raw_data_visible is False


# ---------------------------------------------------------------------------
# intersect — permitted_relationship_types
# ---------------------------------------------------------------------------


def test_intersect_permitted_relationship_types_both_empty_means_no_restriction() -> None:
    a = _allowed_policy("trusted_exchange", permitted_relationship_types=[])
    b = _allowed_policy("trusted_exchange", permitted_relationship_types=[])
    assert intersect(a, b).permitted_relationship_types == []


def test_intersect_permitted_relationship_types_empty_plus_nonempty_uses_nonempty() -> None:
    a = _allowed_policy("trusted_exchange", permitted_relationship_types=[])
    b = _allowed_policy(
        "trusted_exchange",
        permitted_relationship_types=["same_customer", "duplicate_of"],
    )
    # When one side is unrestricted, the other side's allowlist applies.
    assert set(intersect(a, b).permitted_relationship_types) == {
        "same_customer",
        "duplicate_of",
    }


def test_intersect_permitted_relationship_types_both_nonempty_is_set_intersection() -> None:
    a = _allowed_policy(
        "trusted_exchange",
        permitted_relationship_types=["same_customer", "duplicate_of", "supersedes"],
    )
    b = _allowed_policy(
        "trusted_exchange",
        permitted_relationship_types=["duplicate_of", "supersedes", "related_to"],
    )
    result = intersect(a, b)
    assert set(result.permitted_relationship_types) == {"duplicate_of", "supersedes"}


# ---------------------------------------------------------------------------
# is_cross_tenant_match_permitted
# ---------------------------------------------------------------------------


def test_is_cross_tenant_match_permitted_false_when_not_allowed() -> None:
    p = CrossTenantPolicy(allowed=False, sharing_scope="trusted_exchange")
    assert is_cross_tenant_match_permitted(p) is False


def test_is_cross_tenant_match_permitted_false_for_tenant_private() -> None:
    p = CrossTenantPolicy(allowed=True, sharing_scope="tenant_private")
    assert is_cross_tenant_match_permitted(p) is False


def test_is_cross_tenant_match_permitted_false_for_disabled() -> None:
    p = CrossTenantPolicy(allowed=True, sharing_scope="disabled")
    assert is_cross_tenant_match_permitted(p) is False


def test_is_cross_tenant_match_permitted_true_for_three_open_scopes() -> None:
    for scope in ("fingerprint_only", "semantic_only", "trusted_exchange"):
        p = CrossTenantPolicy(allowed=True, sharing_scope=scope)
        assert is_cross_tenant_match_permitted(p) is True, (
            f"scope={scope!r} with allowed=True should permit cross-tenant match"
        )
