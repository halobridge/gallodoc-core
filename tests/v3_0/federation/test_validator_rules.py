"""Codex 08 — v3 validator rules 4 + 5 for the federation block.

Rule 4: federation.cross_tenant_policy.sharing_scope must be in the
        5-value enum (Decision 4).
Rule 5: federation.matching_receipts[].raw_data_exposed must be ``false``
        in v3.0 — receipts may carry hashes and refs only.

Also confirms cross-prompt coverage of Codex 01 Rule 2 (banning
``extensions.halobridge.federation``).
"""

from __future__ import annotations

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


# ---------------------------------------------------------------------------
# Block optionality
# ---------------------------------------------------------------------------


def test_federation_absent_is_valid() -> None:
    """The federation block is optional — absent envelopes validate fine."""
    env = minimal_v3_envelope()
    assert "federation" not in env
    result = validate_envelope(env)
    assert result.valid, (
        f"envelope without federation should validate: "
        f"{[(i.path, i.message) for i in result.errors()]}"
    )


# ---------------------------------------------------------------------------
# Rule 4 — sharing_scope enum
# ---------------------------------------------------------------------------


def test_sharing_scope_fingerprint_only_valid() -> None:
    env = minimal_v3_envelope()
    env["federation"] = {
        "schema_version": "gallodoc.federation.v3.0",
        "cross_tenant_policy": {
            "allowed": True,
            "sharing_scope": "fingerprint_only",
        },
    }
    result = validate_envelope(env)
    assert result.valid, (
        f"sharing_scope=fingerprint_only should validate: "
        f"{[(i.path, i.message) for i in result.errors()]}"
    )


def test_sharing_scope_invalid_value_rejected() -> None:
    env = minimal_v3_envelope()
    env["federation"] = {
        "schema_version": "gallodoc.federation.v3.0",
        "cross_tenant_policy": {
            "allowed": True,
            "sharing_scope": "wonky_value",
        },
    }
    result = validate_envelope(env)
    assert not result.valid, "wonky sharing_scope value must be rejected"
    matching = [
        i
        for i in result.errors()
        if i.path == "federation.cross_tenant_policy.sharing_scope"
        and "wonky_value" in i.message
    ]
    assert matching, (
        f"expected Rule 4 issue for invalid sharing_scope, got "
        f"{[(i.path, i.message) for i in result.errors()]}"
    )


def test_sharing_scope_all_valid_values_pass() -> None:
    """All 5 enum values pass Rule 4."""
    for scope in (
        "tenant_private",
        "fingerprint_only",
        "semantic_only",
        "trusted_exchange",
        "disabled",
    ):
        env = minimal_v3_envelope()
        env["federation"] = {
            "schema_version": "gallodoc.federation.v3.0",
            "cross_tenant_policy": {"allowed": True, "sharing_scope": scope},
        }
        result = validate_envelope(env)
        assert result.valid, (
            f"sharing_scope={scope!r} should validate: "
            f"{[(i.path, i.message) for i in result.errors()]}"
        )


# ---------------------------------------------------------------------------
# Rule 5 — raw_data_exposed must be false in v3.0
# ---------------------------------------------------------------------------


def test_matching_receipt_raw_data_exposed_false_is_valid() -> None:
    env = minimal_v3_envelope()
    env["federation"] = {
        "schema_version": "gallodoc.federation.v3.0",
        "matching_receipts": [
            {
                "matching_id": "match_001",
                "source_profile_ref": "tenant://abc",
                "target_profile_ref": "tenant://def",
                "method": "fingerprint_only",
                "confidence": 0.7,
                "policy_outcome_ref": "",
                "raw_data_exposed": False,
                "created_at": "2026-05-17T00:00:00Z",
            }
        ],
    }
    result = validate_envelope(env)
    assert result.valid, (
        f"raw_data_exposed=false should validate: "
        f"{[(i.path, i.message) for i in result.errors()]}"
    )


def test_matching_receipt_raw_data_exposed_true_rejected() -> None:
    env = minimal_v3_envelope()
    env["federation"] = {
        "schema_version": "gallodoc.federation.v3.0",
        "matching_receipts": [
            {
                "matching_id": "match_001",
                "source_profile_ref": "tenant://abc",
                "target_profile_ref": "tenant://def",
                "method": "fingerprint_only",
                "confidence": 0.7,
                "policy_outcome_ref": "",
                "raw_data_exposed": True,  # Rule 5 violation
                "created_at": "2026-05-17T00:00:00Z",
            }
        ],
    }
    result = validate_envelope(env)
    assert not result.valid, "raw_data_exposed=true must be rejected"
    matching = [
        i
        for i in result.errors()
        if i.path == "federation.matching_receipts[0].raw_data_exposed"
        and "raw_data_exposed must be false" in i.message
    ]
    assert matching, (
        f"expected Rule 5 issue for raw_data_exposed=true, got "
        f"{[(i.path, i.message) for i in result.errors()]}"
    )


def test_multiple_receipts_each_checked_for_raw_data_exposed() -> None:
    """Rule 5 reports a separate issue for each offending receipt."""
    env = minimal_v3_envelope()
    env["federation"] = {
        "schema_version": "gallodoc.federation.v3.0",
        "matching_receipts": [
            {
                "matching_id": "match_001",
                "method": "fingerprint_only",
                "confidence": 0.5,
                "raw_data_exposed": False,
                "created_at": "2026-05-17T00:00:00Z",
            },
            {
                "matching_id": "match_002",
                "method": "trusted_exchange",
                "confidence": 0.8,
                "raw_data_exposed": True,  # offending
                "created_at": "2026-05-17T00:00:00Z",
            },
            {
                "matching_id": "match_003",
                "method": "semantic_only",
                "confidence": 0.6,
                "raw_data_exposed": True,  # offending
                "created_at": "2026-05-17T00:00:00Z",
            },
        ],
    }
    result = validate_envelope(env)
    assert not result.valid
    offending_paths = {
        i.path
        for i in result.errors()
        if "raw_data_exposed" in i.path and "raw_data_exposed must be false" in i.message
    }
    assert offending_paths == {
        "federation.matching_receipts[1].raw_data_exposed",
        "federation.matching_receipts[2].raw_data_exposed",
    }, f"expected receipts [1] and [2] to be flagged, got {offending_paths}"


# ---------------------------------------------------------------------------
# Cross-prompt — Codex 01 Rule 2 still bans extensions.halobridge.federation
# ---------------------------------------------------------------------------


def test_extensions_halobridge_federation_still_rejected() -> None:
    """Codex 01 Rule 2 — confirmed cross-prompt coverage from Codex 08."""
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {"federation": {"any": "shape"}}}
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i
        for i in result.errors()
        if i.path == "extensions.halobridge.federation" and "federation" in i.message
    ]
    assert matching, (
        f"expected Rule 2 ban on extensions.halobridge.federation, got "
        f"{[(i.path, i.message) for i in result.errors()]}"
    )
