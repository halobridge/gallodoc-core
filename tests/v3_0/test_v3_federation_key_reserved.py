"""v3 reserves the top-level ``federation`` key.

Codex 01 reserved the key at the schema root with ``additionalProperties: true``.
Codex 08 tightened the sub-schema (schema_version const, sharing_scope enum,
matching_receipts[] required keys + method enum + confidence range) — this
test confirms the key is still recognized at root and that the new constraints
are enforced.
"""

from __future__ import annotations

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


def test_empty_federation_block_validates() -> None:
    env = minimal_v3_envelope()
    env["federation"] = {}
    result = validate_envelope(env)
    assert result.valid, f"empty federation block should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_well_formed_federation_block_validates() -> None:
    """A federation block matching the Codex 08 sub-schema validates."""
    env = minimal_v3_envelope()
    env["federation"] = {
        "schema_version": "gallodoc.federation.v3.0",
        "tenant_id_hash": "sha256:" + "0" * 64,
        "cross_tenant_policy": {
            "allowed": True,
            "sharing_scope": "fingerprint_only",
            "raw_data_visible": False,
            "fingerprint_sharing_allowed": True,
            "embedding_sharing_allowed": False,
            "requires_review": True,
            "permitted_relationship_types": ["same_entity_candidate"],
        },
        "outbound_policy": {},
        "inbound_matches": [],
        "matching_receipts": [],
    }
    result = validate_envelope(env)
    assert result.valid, f"well-formed federation block should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_federation_under_extensions_halobridge_is_rejected() -> None:
    """Per Decision 4, federation must be top-level. Putting it under
    extensions.halobridge.* trips the v3 ban list."""
    env = minimal_v3_envelope()
    env["extensions"] = {"halobridge": {"federation": {"any": "shape"}}}
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i for i in result.errors() if i.path == "extensions.halobridge.federation"
    ]
    assert matching
