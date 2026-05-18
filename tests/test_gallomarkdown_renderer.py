"""Tests for the GalloMarkdown renderer (GalloDoc JSON → ``.gmd``).

These tests prove that:

* known top-level sections render to the expected ``::block`` form,
* unsafe content is replaced with ``[REDACTED]`` and a warning block,
* rendered output compiles back to a valid GalloDoc envelope, and
* canonical fields survive a full roundtrip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.markdown import gallomd_to_gallodoc
from gallodoc.markdown_renderer import (
    REDACTED,
    gallodoc_to_gallomd,
    render_gallodoc_section,
    render_gallodoc_summary,
)
from gallodoc.validation import validate_envelope


REPO_ROOT = Path(__file__).resolve().parent.parent
V16_EXAMPLE = REPO_ROOT / "examples" / "v1_6" / "gallodoc_agent_supply_chain_security.json"
V15_EXAMPLE = REPO_ROOT / "examples" / "v1_5" / "gallodoc_trust_decision.json"


def _basic_envelope() -> dict:
    return {
        "schema_version": "gallodoc-core/v1",
        "profile": "open-core",
        "identity": {
            "gallodoc_id": "doc-render-001",
            "document_id": "doc-render-001",
            "title": "Renderer Demo",
            "document_type": "demo",
            "mime_type": "text/markdown",
            "schema_version": "gallodoc-core/v1",
        },
        "source": {"source_system": "test", "source_kind": "synthetic"},
        "purpose": {"primary_intent": "demo", "workflow_intent": "renderer_test"},
        "lifecycle": {"available": False},
        "activity": {"available": False, "event_count": 0, "counts_by_type": {}, "latest_events": []},
        "relationships": [],
        "evidence": {
            "count": 1,
            "refs": [
                {"evidence_id": "ev-001", "source_ref": "doc:page-2", "hash": "sha256:abc", "summary": "Anchor."}
            ],
        },
        "validations": {"contradictions": [], "packet_findings": [], "model_disagreements": []},
        "security": {
            "phi_detected": False,
            "phi_categories": [],
            "phi_risk_level": "none",
            "encrypted": False,
            "encrypted_fields": [],
            "masked_fields": [],
            "raw_export_allowed": True,
            "encryption_policy_status": "not_required",
        },
        "exports": [],
        "extensions": {
            "gallomd_artifacts": [
                {"id": "art-001", "family": "line_items", "data": {"description": "Service A", "amount": 100}}
            ]
        },
        "ai_usage": {"summary": {"total_runs": 0}, "runs": []},
        "gallounits": {"unit_strategy": "gallounit_v1", "units": [], "model_projections": []},
        "certification": {"status": "none", "certification_type": "none"},
        "gstp": {"package_id": "", "package_type": "gallodoc_secure_transport_package", "status": "not_created"},
        "truth_ledger": {"available": False, "claim_count": 0, "event_count": 0, "truth_state": "uncertified"},
    }


def test_renders_basic_envelope_to_gallomd() -> None:
    env = _basic_envelope()
    md = gallodoc_to_gallomd(env)
    # Title H1 carries an emoji prefix per the renderer style.
    assert "# 📄 GalloDoc: Renderer Demo" in md
    assert "::gallodoc" in md
    assert "doc_id: doc-render-001" in md
    assert "::" in md


def test_renders_artifacts_blocks() -> None:
    env = _basic_envelope()
    md = gallodoc_to_gallomd(env)
    assert "::artifact family=line_items id=art-001" in md
    assert "description: Service A" in md


def test_renders_evidence_blocks() -> None:
    env = _basic_envelope()
    md = gallodoc_to_gallomd(env)
    assert "::evidence id=ev-001" in md
    assert "source_ref: doc:page-2" in md


def test_renders_trust_and_decision_blocks_from_v16_example() -> None:
    envelope = json.loads(V16_EXAMPLE.read_text(encoding="utf-8"))
    md = gallodoc_to_gallomd(envelope)
    assert "## 🎯 Trust" in md
    assert "## ✅ Decisions" in md
    assert "::trust score=72" in md
    assert "::decision action=install_agent_package" in md


def test_renders_agent_security_blocks_from_v16_example() -> None:
    envelope = json.loads(V16_EXAMPLE.read_text(encoding="utf-8"))
    md = gallodoc_to_gallomd(envelope)
    assert "## 🛡️ Agent Supply Chain Security" in md
    assert "::agent_security" in md
    assert "browser_agent_permission_risk" in md


def test_unsafe_raw_prompt_key_is_redacted() -> None:
    env = _basic_envelope()
    env["extensions"]["gallomd_artifacts"][0]["data"]["raw_prompt"] = "should not survive"
    md = gallodoc_to_gallomd(env)
    assert REDACTED in md
    assert "::warning type=safety_redaction" in md
    assert "should not survive" not in md


def test_private_key_marker_in_value_is_redacted() -> None:
    env = _basic_envelope()
    env["evidence"]["refs"][0]["summary"] = "Found -----BEGIN RSA PRIVATE KEY-----abc-----END RSA PRIVATE KEY-----"
    md = gallodoc_to_gallomd(env)
    assert REDACTED in md
    assert "::warning type=safety_redaction" in md
    assert "BEGIN RSA PRIVATE KEY" not in md


def test_ssn_in_purpose_text_is_redacted() -> None:
    env = _basic_envelope()
    env["purpose"]["reason_text"] = "Note: SSN 123-45-6789 was leaked."
    md = gallodoc_to_gallomd(env)
    assert "123-45-6789" not in md
    assert "::warning type=safety_redaction" in md


def test_rendered_gallomd_compiles_back_to_valid_gallodoc() -> None:
    env = _basic_envelope()
    md = gallodoc_to_gallomd(env)
    env2 = gallomd_to_gallodoc(md)
    result = validate_envelope(env2)
    assert result.valid, [(i.path, i.message) for i in result.issues if i.severity == "error"]


def test_roundtrip_preserves_canonical_fields() -> None:
    envelope = json.loads(V15_EXAMPLE.read_text(encoding="utf-8"))
    md = gallodoc_to_gallomd(envelope)
    env2 = gallomd_to_gallodoc(md)
    assert env2["identity"]["gallodoc_id"] == envelope["identity"]["gallodoc_id"]
    assert env2["identity"]["document_type"] == envelope["identity"]["document_type"]
    assert (
        len(env2.get("trust_decision", {}).get("trust_scores", []))
        == len(envelope["trust_decision"]["trust_scores"])
    )
    assert (
        len(env2.get("trust_decision", {}).get("decision_gates", []))
        == len(envelope["trust_decision"]["decision_gates"])
    )


def test_render_summary_returns_short_overview() -> None:
    env = _basic_envelope()
    summary = render_gallodoc_summary(env)
    assert "# 📄 GalloDoc: Renderer Demo" in summary
    assert "## ✨ Summary" in summary
    # The doc_id appears in both the gallodoc header block and the summary list.
    assert "doc-render-001" in summary


def test_render_section_individual_blocks() -> None:
    env = _basic_envelope()
    artifacts = render_gallodoc_section("artifacts", env)
    assert "::artifact" in artifacts
    evidence = render_gallodoc_section("evidence", env)
    assert "::evidence" in evidence


def test_render_section_unknown_section_raises() -> None:
    with pytest.raises(ValueError):
        render_gallodoc_section("does_not_exist", {})
