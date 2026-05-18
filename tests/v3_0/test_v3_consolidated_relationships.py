"""v3 relationships block consolidates v1 (bare array) + v2.0 (document_relationships)
into a single object with ``relationships[]`` carrying the v2.0 shape plus
required ``status`` and ``discovered_by`` fields per entry.
"""

from __future__ import annotations

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


def test_v20_shaped_relationships_validate_as_v3() -> None:
    """A v2.0 document_relationships-shaped payload rehosted under the v3
    `relationships` key validates."""
    env = minimal_v3_envelope()
    env["relationships"] = {
        "schema_version": "gallodoc.relationships.v3.0",
        "relationships": [
            {
                "relationship_id": "rel-001",
                "source_document_ref": "doc-source",
                "target_document_ref": "doc-target",
                "relationship_type": "version_of",
                "status": "confirmed",
                "discovered_by": "human_review",
                "confidence": 0.95,
                "created_at": "2026-05-16T00:00:00+00:00",
            }
        ],
        "relationship_evidence": [
            {
                "evidence_id": "rev-001",
                "relationship_id": "rel-001",
                "evidence_type": "exact_hash",
                "field_name": "identity.content_hash",
                "value_hash": "sha256:" + "a" * 64,
                "explanation_summary": "Content hashes match.",
            }
        ],
        "relationship_decisions": [
            {
                "decision_id": "rdec-001",
                "relationship_id": "rel-001",
                "decision": "confirmed",
                "decided_by_role": "ops_reviewer",
                "decided_at": "2026-05-16T00:05:00+00:00",
                "reason_code": "exact_hash_match",
            }
        ],
    }
    result = validate_envelope(env)
    assert result.valid, f"v2.0-shaped relationships should validate as v3: {[(i.path, i.message) for i in result.errors()]}"


def test_relationship_missing_status_is_rejected() -> None:
    env = minimal_v3_envelope()
    env["relationships"]["relationships"] = [
        {
            "relationship_id": "rel-001",
            "source_document_ref": "doc-a",
            "target_document_ref": "doc-b",
            "relationship_type": "supports",
            # status missing
            "discovered_by": "human_review",
        }
    ]
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i
        for i in result.errors()
        if "relationships[0].status" in i.path and "required field missing" in i.message
    ]
    assert matching, f"expected status required-missing issue, got {[(i.path, i.message) for i in result.errors()]}"


def test_relationship_missing_discovered_by_is_rejected() -> None:
    env = minimal_v3_envelope()
    env["relationships"]["relationships"] = [
        {
            "relationship_id": "rel-001",
            "source_document_ref": "doc-a",
            "target_document_ref": "doc-b",
            "relationship_type": "supports",
            "status": "confirmed",
            # discovered_by missing
        }
    ]
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i
        for i in result.errors()
        if "relationships[0].discovered_by" in i.path and "required field missing" in i.message
    ]
    assert matching, f"expected discovered_by required-missing issue, got {[(i.path, i.message) for i in result.errors()]}"


def test_relationship_status_must_be_closed_enum() -> None:
    env = minimal_v3_envelope()
    env["relationships"]["relationships"] = [
        {
            "relationship_id": "rel-001",
            "source_document_ref": "doc-a",
            "target_document_ref": "doc-b",
            "relationship_type": "supports",
            "status": "pending",  # not in enum
            "discovered_by": "human_review",
        }
    ]
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i
        for i in result.errors()
        if "relationships[0].status" in i.path and "enum" in i.message.lower()
    ]
    assert matching, f"expected status enum issue, got {[(i.path, i.message) for i in result.errors()]}"


def test_v3_relationships_is_object_not_bare_array() -> None:
    """v1 had relationships as a bare array. v3 requires an object. If we
    pass a bare array (the v1 shape), structural validation fails."""
    env = minimal_v3_envelope()
    env["relationships"] = [
        {"relationship_type": "supports", "source_document_id": "a", "target_document_id": "b"}
    ]
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i for i in result.errors() if i.path == "relationships" and "expected type object" in i.message
    ]
    assert matching, f"expected type-object error at relationships, got {[(i.path, i.message) for i in result.errors()]}"
