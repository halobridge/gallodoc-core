"""Federation-aware policy_check integration tests for the NL→GQL planner.

Verifies the planner's `federation_intersection` policy_check is
emitted with `scopes_allowed` derived from the source envelope's
`federation.cross_tenant_policy.sharing_scope`, per Decision 4 and the
mapping documented in `gallodoc-core-v3-aibi-planner.md §9`.
"""

from __future__ import annotations

import pytest

from gallodoc.aibi import plan


def _envelope_with_scope(scope: str) -> dict:
    return {
        "schema_version": "gallodoc-core/v3",
        "federation": {
            "cross_tenant_policy": {
                "allowed": True,
                "sharing_scope": scope,
            },
        },
    }


def _federation_check(p) -> dict | None:
    for c in p.policy_checks:
        if c.check == "federation_intersection":
            return c.to_dict()
    return None


# ---------------------------------------------------------------------------
# Scope mapping
# ---------------------------------------------------------------------------

def test_tenant_private_envelope_no_federation_check() -> None:
    # tenant_private is a no-op — the planner should not flag the query
    # as cross-tenant based on envelope alone.
    env = _envelope_with_scope("tenant_private")
    p = plan("show invoices linked to John", env)
    assert _federation_check(p) is None


def test_tenant_private_explicit_cross_tenant_keyword_empty_scopes() -> None:
    # If the NL explicitly says cross-tenant but the envelope is
    # tenant_private, the federation check is emitted with empty scopes
    # (no scope permits matching).
    env = _envelope_with_scope("tenant_private")
    p = plan("show invoices linked to John across tenants", env)
    check = _federation_check(p)
    assert check is not None
    assert check["scopes_allowed"] == []


def test_fingerprint_only_scope_mapping() -> None:
    env = _envelope_with_scope("fingerprint_only")
    p = plan("show invoices linked to John across tenants", env)
    check = _federation_check(p)
    assert check is not None
    assert set(check["scopes_allowed"]) == {"fingerprint_only", "trusted_exchange"}


def test_semantic_only_scope_mapping() -> None:
    env = _envelope_with_scope("semantic_only")
    p = plan("show invoices linked to John across tenants", env)
    check = _federation_check(p)
    assert check is not None
    assert set(check["scopes_allowed"]) == {"semantic_only", "trusted_exchange"}


def test_trusted_exchange_scope_mapping() -> None:
    env = _envelope_with_scope("trusted_exchange")
    p = plan("show invoices linked to John across tenants", env)
    check = _federation_check(p)
    assert check is not None
    assert set(check["scopes_allowed"]) == {
        "fingerprint_only",
        "semantic_only",
        "trusted_exchange",
    }


# ---------------------------------------------------------------------------
# Trigger detection
# ---------------------------------------------------------------------------

def test_nl_cross_tenant_keyword_triggers_check() -> None:
    p = plan("show invoices linked to John across tenants")
    assert _federation_check(p) is not None


def test_nl_cross_hyphen_tenant_triggers_check() -> None:
    p = plan("show invoices linked to John cross-tenant", _envelope_with_scope("fingerprint_only"))
    assert _federation_check(p) is not None


def test_no_cross_tenant_phrase_no_federation_envelope_no_check() -> None:
    # NL without cross-tenant language and no federation block → no check.
    p = plan("show invoices linked to John", envelope=None)
    assert _federation_check(p) is None


def test_envelope_with_fingerprint_only_triggers_without_nl_phrase() -> None:
    # Envelope-derived trigger: a non-tenant_private federation block
    # in the envelope is enough to flag the query as cross-tenant.
    env = _envelope_with_scope("fingerprint_only")
    p = plan("show invoices linked to John", env)
    check = _federation_check(p)
    assert check is not None
    assert set(check["scopes_allowed"]) == {"fingerprint_only", "trusted_exchange"}


# ---------------------------------------------------------------------------
# Decision 4 spec check: fingerprint_only sources allow matching against
# fingerprint_only + trusted_exchange remotes (the two scopes that both
# admit fingerprint signals).
# ---------------------------------------------------------------------------

def test_fingerprint_only_excludes_semantic_only() -> None:
    env = _envelope_with_scope("fingerprint_only")
    p = plan("show invoices linked to John across tenants", env)
    check = _federation_check(p)
    assert check is not None
    assert "semantic_only" not in check["scopes_allowed"]
