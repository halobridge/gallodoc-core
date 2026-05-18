"""Validator tests for the GalloDoc Core v2.0 optional blocks.

These exercise:

* schema_version constants per block,
* forbidden-key sets per block,
* obvious secret patterns,
* raw SQL in `query_access`,
* raw vector / chunk text in `vector_context`,
* PHI-shaped literals (SSN-shaped strings) under v2.0 blocks,
* enum / range / timestamp shape checks,
* and that v1.0–v1.6 + v2.0 reference example all still validate.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gallodoc.validation import validate_envelope


V20_BLOCKS = (
    "query_access",
    "vector_context",
    "document_relationships",
    "temporal_versions",
    "policy_governance",
    "access_control",
    "human_review",
    "workflow_execution",
    "connector_lineage",
    "compute_trace",
    "artifact_bom",
)


def _clone(env: dict) -> dict:
    return copy.deepcopy(env)


def test_v20_reference_example_validates(v20_base_envelope):
    r = validate_envelope(_clone(v20_base_envelope))
    assert r.valid, [i.message for i in r.errors()]


def test_v1_examples_still_validate(
    example_envelopes,
    example_envelopes_v11,
    example_envelopes_v12,
    example_envelopes_v13,
    example_envelopes_v14,
    example_envelopes_v15,
    example_envelopes_v16,
):
    bundles = (
        example_envelopes,
        example_envelopes_v11,
        example_envelopes_v12,
        example_envelopes_v13,
        example_envelopes_v14,
        example_envelopes_v15,
        example_envelopes_v16,
    )
    for bundle in bundles:
        for name, env in bundle.items():
            r = validate_envelope(env)
            assert r.valid, f"{name}: {[i.message for i in r.errors()]}"


# ---------------------------------------------------------------------------
# schema_version constants per block
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("block", V20_BLOCKS)
def test_v20_block_rejects_wrong_schema_version(v20_base_envelope, block):
    env = _clone(v20_base_envelope)
    env[block]["schema_version"] = "gallodoc.wrong.v9.9"
    r = validate_envelope(env)
    assert not r.valid
    assert any(f"{block}.schema_version" in i.path for i in r.errors())


@pytest.mark.parametrize("block", V20_BLOCKS)
def test_v20_block_rejects_non_object(v20_base_envelope, block):
    env = _clone(v20_base_envelope)
    env[block] = ["not", "an", "object"]
    r = validate_envelope(env)
    assert not r.valid


# ---------------------------------------------------------------------------
# forbidden-key sets per block (universal raw-* / secret keys)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "block,forbidden_key",
    [
        ("query_access", "raw_prompt"),
        ("vector_context", "raw_response"),
        ("document_relationships", "ssn"),
        ("temporal_versions", "raw_phi"),
        ("policy_governance", "private_key"),
        ("access_control", "session_hash"),
        ("human_review", "tenant_id"),
        ("workflow_execution", "ip_hash"),
        ("connector_lineage", "password"),
        ("compute_trace", "api_key"),
        ("artifact_bom", "bearer_token"),
    ],
)
def test_v20_block_rejects_universal_forbidden_key(v20_base_envelope, block, forbidden_key):
    env = _clone(v20_base_envelope)
    env[block][forbidden_key] = "value-should-not-pass"
    r = validate_envelope(env)
    assert not r.valid
    assert any("forbidden key under v2.0 block" in i.message for i in r.errors())


@pytest.mark.parametrize(
    "block,forbidden_key",
    [
        ("query_access", "raw_sql"),
        ("query_access", "sql_text"),
        ("vector_context", "raw_vector"),
        ("vector_context", "embedding_vector"),
        ("vector_context", "chunk_text"),
        ("document_relationships", "raw_field_value"),
        ("temporal_versions", "raw_before"),
        ("policy_governance", "rego_source"),
        ("access_control", "user_email"),
        ("human_review", "raw_notes"),
        ("workflow_execution", "raw_input"),
        ("connector_lineage", "credential"),
        ("compute_trace", "raw_log"),
        ("artifact_bom", "exploit_payload"),
    ],
)
def test_v20_block_rejects_per_block_forbidden_key(v20_base_envelope, block, forbidden_key):
    env = _clone(v20_base_envelope)
    env[block][forbidden_key] = "should-not-leak"
    r = validate_envelope(env)
    assert not r.valid


# ---------------------------------------------------------------------------
# Obvious secret-shaped strings (JWT) inside v2.0 blocks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("block", V20_BLOCKS)
def test_v20_block_rejects_jwt_shaped_string(v20_base_envelope, block):
    env = _clone(v20_base_envelope)
    env[block]["debug_payload"] = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.not-a-real-signature-but-jwt-shaped"
    r = validate_envelope(env)
    assert not r.valid
    assert any("JWT" in i.message for i in r.errors())


# ---------------------------------------------------------------------------
# query_access — raw SQL must fail
# ---------------------------------------------------------------------------


def test_query_access_rejects_raw_sql_field(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["query_access"]["saved_queries"][0]["raw_sql"] = "SELECT * FROM patients;"
    r = validate_envelope(env)
    assert not r.valid


def test_query_access_rejects_sql_text_field(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["query_access"]["saved_queries"][0]["sql_text"] = "SELECT mrn FROM patients WHERE id=1"
    r = validate_envelope(env)
    assert not r.valid


def test_query_access_safe_filters_pass(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["query_access"]["saved_queries"][0]["filters"] = {
        "subject_type": "document",
        "score_lt": 80,
    }
    r = validate_envelope(env)
    assert r.valid, [i.message for i in r.errors()]


# ---------------------------------------------------------------------------
# vector_context — raw vector / chunk_text must fail
# ---------------------------------------------------------------------------


def test_vector_context_rejects_raw_vector(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["vector_context"]["embedding_chunks"][0]["raw_vector"] = [0.01] * 16
    r = validate_envelope(env)
    assert not r.valid


def test_vector_context_rejects_chunk_text(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["vector_context"]["embedding_chunks"][0]["chunk_text"] = "patient bob smith ssn 123-45-6789"
    r = validate_envelope(env)
    assert not r.valid


def test_vector_context_hash_only_passes(v20_base_envelope):
    """Hashes-only chunk shape passes — proves the safe path is allowed."""
    env = _clone(v20_base_envelope)
    env["vector_context"]["embedding_chunks"] = [{
        "chunk_id": "c-001",
        "source_artifact_ref": "artifact:body",
        "source_span": "p1",
        "text_hash": "txh_" + "a" * 60,
        "token_count": 256,
        "embedding_hash": "eh_" + "a" * 60,
        "model_hash_or_id": "model_demo",
        "metadata_summary": "redacted",
        "created_at": "2026-04-15T00:00:00+00:00",
    }]
    r = validate_envelope(env)
    assert r.valid, [i.message for i in r.errors()]


# ---------------------------------------------------------------------------
# PHI-like literals under v2.0 blocks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("block", V20_BLOCKS)
def test_v20_block_rejects_ssn_shaped_string(v20_base_envelope, block):
    env = _clone(v20_base_envelope)
    env[block]["sample_text"] = "subject ssn 123-45-6789 in synthetic data"
    r = validate_envelope(env)
    assert not r.valid
    assert any("SSN-shaped" in i.message for i in r.errors())


@pytest.mark.parametrize("block", V20_BLOCKS)
def test_v20_block_rejects_disallowed_email(v20_base_envelope, block):
    env = _clone(v20_base_envelope)
    env[block]["sample_text"] = "send to user@evil-corp.invalid"
    r = validate_envelope(env)
    assert not r.valid
    assert any("email" in i.message.lower() for i in r.errors())


# ---------------------------------------------------------------------------
# enum / range / timestamp shape checks
# ---------------------------------------------------------------------------


def test_document_relationships_rejects_bad_enum(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["document_relationships"]["relationships"][0]["relationship_type"] = "invalid_kind"
    r = validate_envelope(env)
    assert not r.valid
    assert any("relationship_type" in i.path for i in r.errors())


def test_document_relationships_rejects_bad_confidence(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["document_relationships"]["relationships"][0]["confidence"] = 4.2
    r = validate_envelope(env)
    assert not r.valid
    assert any("confidence" in i.path for i in r.errors())


def test_temporal_versions_rejects_bad_status(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["temporal_versions"]["versions"][0]["status"] = "wat"
    r = validate_envelope(env)
    assert not r.valid


def test_temporal_versions_rejects_bad_change_type(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["temporal_versions"]["change_events"][0]["change_type"] = "totally_made_up"
    r = validate_envelope(env)
    assert not r.valid


def test_policy_governance_rejects_bad_language(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["policy_governance"]["policy_sets"][0]["language"] = "yaml_rules"
    r = validate_envelope(env)
    assert not r.valid


def test_access_control_rejects_bad_decision(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["access_control"]["access_receipts"][0]["decision"] = "shrug"
    r = validate_envelope(env)
    assert not r.valid


def test_human_review_rejects_bad_action(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["human_review"]["review_actions"][0]["action"] = "fire_it_into_the_sun"
    r = validate_envelope(env)
    assert not r.valid


def test_workflow_execution_rejects_bad_step_type(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["workflow_execution"]["workflow_steps"][0]["step_type"] = "manifest_destiny"
    r = validate_envelope(env)
    assert not r.valid


def test_compute_trace_rejects_bad_span_type(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["compute_trace"]["spans"][0]["span_type"] = "vibes"
    r = validate_envelope(env)
    assert not r.valid


def test_artifact_bom_rejects_bad_component_type(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["artifact_bom"]["components"][0]["component_type"] = "soul"
    r = validate_envelope(env)
    assert not r.valid


def test_v20_block_rejects_non_iso_timestamp(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["query_access"]["saved_queries"][0]["created_at"] = "yesterday"
    r = validate_envelope(env)
    assert not r.valid
    assert any("ISO-8601" in i.message for i in r.errors())


def test_v20_block_rejects_negative_max_results(v20_base_envelope):
    env = _clone(v20_base_envelope)
    env["query_access"]["saved_queries"][0]["max_results"] = -5
    r = validate_envelope(env)
    assert not r.valid


# ---------------------------------------------------------------------------
# Required-field missing
# ---------------------------------------------------------------------------


def test_query_access_requires_query_id(v20_base_envelope):
    env = _clone(v20_base_envelope)
    del env["query_access"]["saved_queries"][0]["query_id"]
    r = validate_envelope(env)
    assert not r.valid


def test_workflow_execution_requires_started_at(v20_base_envelope):
    env = _clone(v20_base_envelope)
    del env["workflow_execution"]["workflow_runs"][0]["started_at"]
    r = validate_envelope(env)
    assert not r.valid
