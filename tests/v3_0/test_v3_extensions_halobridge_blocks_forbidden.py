"""v3 validator rule 2: banned ``extensions.halobridge.<known_block>`` keys.

The 13 v1.2–v1.6 compliance block names plus ``federation`` (Decision 4) are
forbidden under ``extensions.halobridge.*`` in v3. These blocks live at top
level only. The migration helper in prompt 02 strips them on upgrade; the
v3 validator prevents them from being re-introduced.

14 banned names total.
"""

from __future__ import annotations

import pytest

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


_BANNED_NAMES = [
    # v1.2 compliance blocks
    "consent_ledger",
    "chain_of_custody",
    "human_decisions",
    "attestations",
    "redaction_manifest",
    "evidence_quality",
    # v1.3 compliance blocks
    "data_residency",
    "training_permissions",
    "model_risk",
    "retention_status",
    # v1.4 amendment
    "agent_observability",
    # v1.5 amendment (also superseded by the v3 trust block)
    "trust_decision",
    # v1.6 amendment
    "agent_supply_chain_security",
    # Decision 4 — federation must be top-level
    "federation",
]


@pytest.mark.parametrize("banned_key", _BANNED_NAMES)
def test_each_banned_key_under_extensions_halobridge_is_rejected(banned_key: str) -> None:
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {banned_key: {"any": "shape"}}}
    result = validate_envelope(env)
    assert not result.valid, f"extensions.halobridge.{banned_key} must be rejected"
    matching = [
        i
        for i in result.errors()
        if i.path == f"extensions.halobridge.{banned_key}"
        and banned_key in i.message
    ]
    assert matching, (
        f"expected forbidden-key issue for {banned_key!r}, "
        f"got {[(i.path, i.message) for i in result.errors()]}"
    )


def test_count_of_banned_names_is_14() -> None:
    """The ban list is exactly 13 v1.2–v1.6 names + federation = 14."""
    assert len(_BANNED_NAMES) == 14


def test_allowed_halobridge_keys_pass() -> None:
    """Non-banned vendor extensions under extensions.halobridge.* are fine."""
    env = minimal_v3_envelope()
    env["extensions"] = {
        "halobridge": {
            "private_summary": {"any": "shape"},
            "internal_telemetry": {"foo": "bar"},
        }
    }
    result = validate_envelope(env)
    # Non-banned keys should not trip the rule.
    forbidden_issues = [i for i in result.issues if "forbidden key" in i.message]
    assert not forbidden_issues
    assert result.valid, f"non-banned extensions.halobridge.* keys should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_other_vendor_namespace_unaffected() -> None:
    """`extensions.<other_vendor>.consent_ledger` is NOT blocked — the rule
    only targets the halobridge subkey to fix the v1.x double-emission bug."""
    env = minimal_v3_envelope()
    env["extensions"] = {"acme": {"consent_ledger": {"shape": "ok"}}}
    result = validate_envelope(env)
    forbidden_issues = [i for i in result.issues if "extensions.halobridge" in i.path]
    assert not forbidden_issues
    assert result.valid


def test_extensions_halobridge_consent_ledger_rejection_message_mentions_block_name() -> None:
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {"consent_ledger": {"entries": []}}}
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i for i in result.errors() if "consent_ledger" in i.path and "consent_ledger" in i.message
    ]
    assert matching
