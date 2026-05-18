"""Negative coverage for `assert_no_enterprise_leakage`.

Asserts each leak shape raises, the clean fixture passes, and multiple
leaks accumulate into a single error message.
"""

from __future__ import annotations

import pytest

from gallodoc.projection.safety import (
    EnterpriseLeakageError,
    assert_no_enterprise_leakage,
)

from tests.v3_0.projection.conftest import minimal_v3_envelope


def test_clean_envelope_passes() -> None:
    assert_no_enterprise_leakage(minimal_v3_envelope())


def test_policy_formula_anywhere_raises() -> None:
    env = minimal_v3_envelope()
    # Nested inside an arbitrary block.
    env["activity"]["latest_events"] = [{"policy_formula": "if x then y"}]
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(env)
    assert "policy_formula" in str(exc.value)


def test_halobridge_internal_anywhere_raises() -> None:
    env = minimal_v3_envelope()
    env["extensions"]["acme"] = {"halobridge_internal": {"internal": True}}
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(env)
    assert "halobridge_internal" in str(exc.value)


def test_double_underscore_internal_anywhere_raises() -> None:
    env = minimal_v3_envelope()
    env["gallounits"]["__internal__"] = {"trace_id": "abc"}
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(env)
    assert "__internal__" in str(exc.value)


def test_surviving_extensions_halobridge_consent_ledger_raises() -> None:
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {"consent_ledger": {"entries": []}}}
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(env)
    assert "consent_ledger" in str(exc.value)


def test_ssn_like_string_raises() -> None:
    env = minimal_v3_envelope()
    env["identity"]["title"] = "Synthetic record 123-45-6789 (fake)"
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(env)
    assert "SSN-like" in str(exc.value)


def test_mrn_like_string_raises() -> None:
    env = minimal_v3_envelope()
    env["identity"]["title"] = "Note: MRN: ABC123456 was redacted"
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(env)
    assert "MRN-like" in str(exc.value)


def test_private_key_shaped_string_raises() -> None:
    env = minimal_v3_envelope()
    # The leak detector matches the literal word inside a string.
    env["identity"]["title"] = "Carries a private_key reference (synthetic)"
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(env)
    assert "private_key" in str(exc.value)


def test_multiple_leaks_combine_into_one_error_message() -> None:
    env = minimal_v3_envelope()
    env["activity"]["latest_events"] = [{"policy_formula": "x"}]
    env["extensions"] = {"halobridge": {"consent_ledger": {}, "chain_of_custody": {}}}
    env["identity"]["title"] = "fake-record SSN 123-45-6789"
    with pytest.raises(EnterpriseLeakageError) as exc:
        assert_no_enterprise_leakage(env)
    msg = str(exc.value)
    # Expect at least 4 issues collated.
    assert "policy_formula" in msg
    assert "consent_ledger" in msg
    assert "chain_of_custody" in msg
    assert "SSN-like" in msg
