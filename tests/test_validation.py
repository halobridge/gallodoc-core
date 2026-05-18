"""Tests for `gallodoc.validation` and the bundled schema."""

from __future__ import annotations

import json

import pytest

from gallodoc import GALLODOC_CORE_VERSION
from gallodoc.schema import (
    frozen_version,
    is_frozen,
    load_schema,
    required_top_level_sections,
)
from gallodoc.validation import (
    ValidationResult,
    validate_envelope,
    validate_with_jsonschema,
)


REQUIRED = (
    "schema_version",
    "identity",
    "source",
    "purpose",
    "lifecycle",
    "activity",
    "relationships",
    "evidence",
    "validations",
    "security",
    "exports",
    "extensions",
    "ai_usage",
    "gallounits",
    "certification",
    "gstp",
    "truth_ledger",
)


def test_schema_loads_and_is_frozen():
    # v1 is still frozen within its scope; pass version explicitly because
    # load_schema() now defaults to v3 (see docs/specs/gallodoc-core-v3-master-spec.md).
    s = load_schema(version="gallodoc-core/v1")
    assert s["title"] == "GalloDoc Core v1"
    assert is_frozen(version="gallodoc-core/v1") is True
    assert frozen_version(version="gallodoc-core/v1") == "gallodoc-core/v1"


def test_required_sections_match_freeze():
    rt = set(required_top_level_sections(version="gallodoc-core/v1"))
    missing = [s for s in REQUIRED if s not in rt]
    assert not missing, f"Required v1 sections missing from schema: {missing}"


def test_validate_returns_failure_for_empty_envelope():
    r = validate_envelope({})
    assert isinstance(r, ValidationResult)
    assert not r.valid
    assert any("schema_version" in i.path for i in r.errors())


def test_validate_examples_pass(example_envelopes):
    failures: list[str] = []
    for name, env in example_envelopes.items():
        r = validate_envelope(env)
        if not r.valid:
            failures.append(f"{name}: " + "; ".join(f"{i.path}={i.message}" for i in r.errors()))
    assert not failures, "Examples failed validation:\n" + "\n".join(failures)


def test_validate_with_jsonschema_falls_back_gracefully(example_envelopes):
    # When jsonschema is not installed, the function still returns a result.
    name, env = next(iter(example_envelopes.items()))
    r = validate_with_jsonschema(env)
    assert r.valid in (True, False)
    # Either the optional path ran (used_jsonschema=True) or we fell back with a warning.
    assert r.used_jsonschema or any(i.severity == "warning" for i in r.issues)


def test_validate_v11_examples_pass(example_envelopes_v11):
    if not example_envelopes_v11:
        pytest.skip("no examples/v1_1/*.json")
    failures: list[str] = []
    for name, env in example_envelopes_v11.items():
        r = validate_envelope(env)
        if not r.valid:
            failures.append(f"{name}: " + "; ".join(f"{i.path}={i.message}" for i in r.errors()))
    assert not failures, "v1.1 examples failed validation:\n" + "\n".join(failures)


def test_execution_governance_rejects_forbidden_keys(example_envelopes):
    """Nested forbidden keys under execution_governance must fail validation."""
    env = json.loads(json.dumps(next(iter(example_envelopes.values()))))
    env["execution_governance"] = {
        "schema_version": "gallodoc.execution_governance.v1.1",
        "capability_tokens": [],
        "mcp_tool_contracts": [{"tool_id": "t", "resource_scope": {"prompt_text": "x"}}],
        "a2a_agent_contracts": [],
        "skill_contracts": [],
        "prompt_contracts": [],
        "delegation_policies": [],
        "execution_requests": [],
        "execution_receipts": [],
    }
    r = validate_envelope(env)
    assert not r.valid
    assert any("prompt_text" in i.path for i in r.errors())


def test_validate_v12_examples_pass(example_envelopes_v12):
    if not example_envelopes_v12:
        pytest.skip("no examples/v1_2/*.json")
    failures: list[str] = []
    for name, env in example_envelopes_v12.items():
        r = validate_envelope(env)
        if not r.valid:
            failures.append(f"{name}: " + "; ".join(f"{i.path}={i.message}" for i in r.errors()))
    assert not failures, "v1.2 examples failed validation:\n" + "\n".join(failures)


def test_validate_v13_examples_pass(example_envelopes_v13):
    if not example_envelopes_v13:
        pytest.skip("no examples/v1_3/*.json")
    failures: list[str] = []
    for name, env in example_envelopes_v13.items():
        r = validate_envelope(env)
        if not r.valid:
            failures.append(f"{name}: " + "; ".join(f"{i.path}={i.message}" for i in r.errors()))
    assert not failures, "v1.3 examples failed validation:\n" + "\n".join(failures)


def test_validate_v14_examples_pass(example_envelopes_v14):
    if not example_envelopes_v14:
        pytest.skip("no examples/v1_4/*.json")
    failures: list[str] = []
    for name, env in example_envelopes_v14.items():
        r = validate_envelope(env)
        if not r.valid:
            failures.append(f"{name}: " + "; ".join(f"{i.path}={i.message}" for i in r.errors()))
    assert not failures, "v1.4 examples failed validation:\n" + "\n".join(failures)


def test_validate_v15_examples_pass(example_envelopes_v15):
    if not example_envelopes_v15:
        pytest.skip("no examples/v1_5/*.json")
    failures: list[str] = []
    for name, env in example_envelopes_v15.items():
        r = validate_envelope(env)
        if not r.valid:
            failures.append(f"{name}: " + "; ".join(f"{i.path}={i.message}" for i in r.errors()))
    assert not failures, "v1.5 examples failed validation:\n" + "\n".join(failures)


def test_trust_decision_rejects_raw_phi_key(example_envelopes_v15):
    if not example_envelopes_v15:
        pytest.skip("no examples/v1_5/*.json")
    env = json.loads(json.dumps(next(iter(example_envelopes_v15.values()))))
    env.setdefault("trust_decision", {})["raw_phi"] = {"patient_name": "leak"}
    r = validate_envelope(env)
    assert not r.valid
    assert any("raw_phi" in i.path for i in r.errors())


def test_validate_v16_examples_pass(example_envelopes_v16):
    if not example_envelopes_v16:
        pytest.skip("no examples/v1_6/*.json")
    failures: list[str] = []
    for name, env in example_envelopes_v16.items():
        r = validate_envelope(env)
        if not r.valid:
            failures.append(f"{name}: " + "; ".join(f"{i.path}={i.message}" for i in r.errors()))
    assert not failures, "v1.6 examples failed validation:\n" + "\n".join(failures)


def test_agent_supply_chain_security_rejects_secret_like_keys(example_envelopes_v16):
    if not example_envelopes_v16:
        pytest.skip("no examples/v1_6/*.json")
    env = json.loads(json.dumps(next(iter(example_envelopes_v16.values()))))
    env["agent_supply_chain_security"]["package_manifests"][0]["raw_secret"] = "do-not-ship"
    r = validate_envelope(env)
    assert not r.valid
    assert any("raw_secret" in i.path for i in r.errors())


def test_agent_observability_rejects_chain_of_thought_key(example_envelopes_v14):
    if not example_envelopes_v14:
        pytest.skip("no examples/v1_4/*.json")
    env = json.loads(json.dumps(next(iter(example_envelopes_v14.values()))))
    env["agent_observability"]["reasoning_summaries"].append(
        {
            "reasoning_id": "bad",
            "trace_id": "550e8400-e29b-41d4-a716-446655440000",
            "reasoning_type": "planning",
            "chain_of_thought": "secret steps",
            "summary": "x",
            "confidence": 0.1,
            "uncertainty_flags": [],
            "decision_rationale_refs": [],
            "evidence_refs": [],
            "redacted": False,
        }
    )
    r = validate_envelope(env)
    assert not r.valid
    assert any("chain_of_thought" in i.path for i in r.errors())


def test_compliance_v13_rejects_training_leak_keys(example_envelopes):
    env = json.loads(json.dumps(next(iter(example_envelopes.values()))))
    env["model_risk"] = {
        "schema_version": "gallodoc.model_risk.v1.3",
        "provider_class": "internal",
        "model_name_hash_or_id": "abc",
        "approval_status": "experimental",
        "phi_allowed": False,
        "external_transmission_allowed": False,
        "max_data_mode": "redacted",
        "reviewed_at": "2026-05-02T12:00:00+00:00",
        "policy_version": "t",
        "training_payload": {},
    }
    r = validate_envelope(env)
    assert not r.valid
    assert any("training_payload" in i.path for i in r.errors())


def test_compliance_v12_rejects_url_string(example_envelopes):
    env = json.loads(json.dumps(next(iter(example_envelopes.values()))))
    env["consent_ledger"] = {
        "schema_version": "gallodoc.consent_ledger.v1.2",
        "entries": [{"consent_id": "x", "consent_artifact_ref": "https://evil.example/leak"}],
    }
    r = validate_envelope(env)
    assert not r.valid


def test_execution_governance_rejects_jwt_shaped_strings(example_envelopes):
    env = json.loads(json.dumps(next(iter(example_envelopes.values()))))
    fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    env["execution_governance"] = {
        "schema_version": "gallodoc.execution_governance.v1.1",
        "capability_tokens": [{"token_id": fake_jwt}],
        "mcp_tool_contracts": [],
        "a2a_agent_contracts": [],
        "skill_contracts": [],
        "prompt_contracts": [],
        "delegation_policies": [],
        "execution_requests": [],
        "execution_receipts": [],
    }
    r = validate_envelope(env)
    assert not r.valid
    assert any("JWT" in i.message for i in r.errors())
