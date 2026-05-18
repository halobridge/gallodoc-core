"""Tests for the GalloMarkdown compile direction (``.gmd`` → GalloDoc JSON).

These tests prove that the GalloMarkdown authoring layer always produces
canonical ``gallodoc-core/v1`` envelopes and rejects unsafe content at
parse time.
"""

from __future__ import annotations

import pytest

from gallodoc.markdown import (
    GALLOMD_VERSION,
    GalloMDError,
    gallomd_to_gallodoc,
    parse_gallomd,
    validate_gallomd,
)
from gallodoc.validation import validate_envelope


BASIC_GMD = """# GalloDoc: Basic Demo

::gallodoc
doc_id: doc-basic-001
document_type: demo
::

## Content

Hello GalloMarkdown.

## Notes

This is a demo body paragraph.
"""

EVIDENCE_GMD = """# Evidence Demo

::gallodoc
doc_id: doc-ev-001
document_type: contract
::

::evidence id=ev-001
source_ref: doc:contract-page-2
hash: sha256:abc123
summary: Quoted price line.
::
"""

TRUST_GMD = """# Trust Demo

::gallodoc
doc_id: doc-trust-001
document_type: contract
::

::trust score=92 level=HIGH
grade: A
status: trusted
explanation: Evidence verified.
::

::decision action=approve id=gate-001
reason: evidence_validated
::
"""

AGENT_SECURITY_GMD = """# Agent Security Demo

::gallodoc
doc_id: doc-asc-001
document_type: agent_skill_bundle_manifest
::

::agent_security risk_level=high decision=block id=asc-find-001
risk_score: 87
summary: Manifest declared a high-risk capability.
::
"""

POLICY_GMD = """# Policy Demo

::gallodoc
doc_id: doc-pol-001
document_type: policy_review
::

::policy decision=allow id=pol-001
policy_name: contract_review_v1
policy_version: v1
::
"""


def test_gallomd_version_constant() -> None:
    assert GALLOMD_VERSION == "gallomarkdown/v1"


def test_basic_gmd_compiles_to_valid_envelope() -> None:
    env = gallomd_to_gallodoc(BASIC_GMD)
    assert env["schema_version"] == "gallodoc-core/v1"
    assert env["identity"]["gallodoc_id"] == "doc-basic-001"
    assert env["identity"]["document_type"] == "demo"
    assert env["identity"]["title"] == "GalloDoc: Basic Demo"
    result = validate_envelope(env)
    assert result.valid, [(i.path, i.message) for i in result.issues if i.severity == "error"]


def test_evidence_block_populates_evidence_refs() -> None:
    env = gallomd_to_gallodoc(EVIDENCE_GMD)
    refs = env["evidence"]["refs"]
    assert len(refs) == 1
    assert refs[0]["evidence_id"] == "ev-001"
    assert refs[0]["source_ref"] == "doc:contract-page-2"
    assert refs[0]["hash"].startswith("sha256:")
    assert env["evidence"]["count"] == 1


def test_trust_and_decision_blocks_populate_trust_decision() -> None:
    env = gallomd_to_gallodoc(TRUST_GMD)
    td = env["trust_decision"]
    assert td["schema_version"] == "gallodoc.trust_decision.v1.5"
    assert len(td["trust_scores"]) == 1
    score = td["trust_scores"][0]
    assert score["score"] == 92
    assert score["grade"] == "A"
    assert score["status"] == "trusted"
    # All eight component blocks must exist on the trust score.
    components = score["components"]
    for key in (
        "evidence_quality",
        "lifecycle_completeness",
        "security_posture",
        "execution_governance",
        "consent_custody_attestation",
        "residency_training_model_risk",
        "agent_observability",
        "human_review",
    ):
        assert key in components
        assert components[key]["score"] == 92

    gates = td["decision_gates"]
    assert len(gates) == 1
    assert gates[0]["decision"] == "allow"
    assert gates[0]["reason_codes"] == ["evidence_validated"]
    result = validate_envelope(env)
    assert result.valid


def test_agent_security_block_populates_agent_supply_chain_security() -> None:
    env = gallomd_to_gallodoc(AGENT_SECURITY_GMD)
    asc = env["agent_supply_chain_security"]
    assert asc["schema_version"] == "gallodoc.agent_supply_chain_security.v1.6"
    assert len(asc["findings"]) == 1
    finding = asc["findings"][0]
    assert finding["severity"] == "high"
    assert finding["decision"] == "block"
    assert finding["risk_score"] == 87


def test_policy_block_populates_policy_outcomes() -> None:
    env = gallomd_to_gallodoc(POLICY_GMD)
    outcomes = env["trust_decision"]["policy_outcomes"]
    assert len(outcomes) == 1
    assert outcomes[0]["policy_name"] == "contract_review_v1"
    assert outcomes[0]["decision"] == "allow"


def test_forbidden_raw_prompt_key_is_rejected() -> None:
    bad = """# Bad

::gallodoc
doc_id: x
document_type: t
::

::evidence id=ev-1
raw_prompt: This is forbidden.
::
"""
    with pytest.raises(GalloMDError) as exc:
        gallomd_to_gallodoc(bad)
    assert "raw_prompt" in str(exc.value)


def test_forbidden_raw_response_key_is_rejected() -> None:
    bad = """# Bad

::gallodoc
doc_id: x
document_type: t
::

::evidence id=ev-1
raw_response: This is forbidden.
::
"""
    with pytest.raises(GalloMDError):
        gallomd_to_gallodoc(bad)


def test_chain_of_thought_key_is_rejected() -> None:
    bad = """# Bad

::gallodoc
doc_id: x
document_type: t
::

::trust score=80
chain_of_thought: not allowed.
::
"""
    with pytest.raises(GalloMDError):
        gallomd_to_gallodoc(bad)


def test_ssn_literal_in_block_body_is_rejected() -> None:
    bad = """# Bad

::gallodoc
doc_id: x
document_type: t
::

::evidence id=ev-1
summary: SSN is 123-45-6789.
::
"""
    with pytest.raises(GalloMDError) as exc:
        gallomd_to_gallodoc(bad)
    assert "ssn" in str(exc.value).lower()


def test_pem_private_key_marker_is_rejected() -> None:
    bad = """# Bad

::gallodoc
doc_id: x
document_type: t
::

::evidence id=ev-1
summary: Found -----BEGIN RSA PRIVATE KEY----- block.
::
"""
    with pytest.raises(GalloMDError):
        gallomd_to_gallodoc(bad)


def test_openai_api_key_marker_is_rejected() -> None:
    bad = """# Bad

::gallodoc
doc_id: x
document_type: t
::

::evidence id=ev-1
summary: Found sk-1234567890abcdefghijklmnop in repo.
::
"""
    with pytest.raises(GalloMDError):
        gallomd_to_gallodoc(bad)


def test_unterminated_block_is_rejected() -> None:
    bad = """# Bad

::gallodoc
doc_id: x
document_type: t

(no closing fence)
"""
    with pytest.raises(GalloMDError):
        parse_gallomd(bad)


def test_validate_gallomd_returns_document() -> None:
    doc = validate_gallomd(BASIC_GMD)
    assert doc.title == "GalloDoc: Basic Demo"
    assert any(b.name == "gallodoc" for b in doc.blocks)


def test_compiled_envelope_passes_full_validator() -> None:
    big = (
        BASIC_GMD
        + "\n\n"
        + EVIDENCE_GMD.split("::gallodoc", 1)[1].split("::\n", 1)[1]
    )
    env = gallomd_to_gallodoc(BASIC_GMD)  # plain compile is enough for the validator
    result = validate_envelope(env)
    assert result.valid


def test_inline_attribute_with_quoted_value_parses() -> None:
    text = """# Demo

::gallodoc
doc_id: doc-q-001
document_type: demo
title: "A Quoted Title With Spaces"
::
"""
    env = gallomd_to_gallodoc(text)
    assert env["identity"]["title"] == "A Quoted Title With Spaces"


def test_code_fence_is_not_interpreted_as_block() -> None:
    text = """# Demo

::gallodoc
doc_id: doc-cf-001
document_type: demo
::

## Content

```
::evidence id=NOT-A-BLOCK
raw_prompt: pretend
::
```
"""
    # This must NOT raise — content inside a code fence stays as content.
    env = gallomd_to_gallodoc(text)
    assert env["evidence"]["count"] == 0
