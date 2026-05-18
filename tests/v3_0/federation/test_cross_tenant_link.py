"""Codex 08 — cross_tenant_link: linker + enforcement integration."""

from __future__ import annotations

from gallodoc.federation import cross_tenant_link
from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


_SHARED_HASH = "sha256:" + "a" * 64


def _envelope_with_units(
    gallodoc_id: str,
    units: list[dict],
    *,
    federation_policy: dict | None = None,
    tenant_hash: str = "sha256:" + "f" * 64,
) -> dict:
    env = minimal_v3_envelope()
    env["identity"]["gallodoc_id"] = gallodoc_id
    env["gallounits"]["units"] = units
    if federation_policy is not None:
        env["federation"] = {
            "schema_version": "gallodoc.federation.v3.0",
            "tenant_id_hash": tenant_hash,
            "cross_tenant_policy": federation_policy,
        }
    return env


_ALLOW_TRUSTED_EXCHANGE = {
    "allowed": True,
    "sharing_scope": "trusted_exchange",
    "raw_data_visible": False,
    "fingerprint_sharing_allowed": True,
    "embedding_sharing_allowed": True,
    "requires_review": False,
    "permitted_relationship_types": [],
}

_DENY_TENANT_PRIVATE = {
    "allowed": False,
    "sharing_scope": "tenant_private",
    "raw_data_visible": False,
    "fingerprint_sharing_allowed": False,
    "embedding_sharing_allowed": False,
    "requires_review": True,
    "permitted_relationship_types": [],
}


# ---------------------------------------------------------------------------
# Two-envelope cases
# ---------------------------------------------------------------------------


def test_both_allowed_trusted_exchange_yields_candidate() -> None:
    src = _envelope_with_units(
        "doc_src",
        [{"unit_id": "u1", "text_hash": _SHARED_HASH}],
        federation_policy=_ALLOW_TRUSTED_EXCHANGE,
        tenant_hash="sha256:" + "a" * 64,
    )
    tgt = _envelope_with_units(
        "doc_tgt",
        [{"unit_id": "u2", "text_hash": _SHARED_HASH}],
        federation_policy=_ALLOW_TRUSTED_EXCHANGE,
        tenant_hash="sha256:" + "b" * 64,
    )
    out = cross_tenant_link(src, [tgt])
    assert len(out.candidates) == 1
    assert out.candidates[0].source_document_id == "doc_src"
    assert out.candidates[0].target_document_id == "doc_tgt"


def test_target_tenant_private_drops_candidate() -> None:
    src = _envelope_with_units(
        "doc_src",
        [{"unit_id": "u1", "text_hash": _SHARED_HASH}],
        federation_policy=_ALLOW_TRUSTED_EXCHANGE,
    )
    tgt = _envelope_with_units(
        "doc_tgt",
        [{"unit_id": "u2", "text_hash": _SHARED_HASH}],
        federation_policy=_DENY_TENANT_PRIVATE,
    )
    out = cross_tenant_link(src, [tgt])
    assert out.candidates == []


def test_source_tenant_private_drops_candidate() -> None:
    """Symmetry — source-side denial is just as effective."""
    src = _envelope_with_units(
        "doc_src",
        [{"unit_id": "u1", "text_hash": _SHARED_HASH}],
        federation_policy=_DENY_TENANT_PRIVATE,
    )
    tgt = _envelope_with_units(
        "doc_tgt",
        [{"unit_id": "u2", "text_hash": _SHARED_HASH}],
        federation_policy=_ALLOW_TRUSTED_EXCHANGE,
    )
    out = cross_tenant_link(src, [tgt])
    assert out.candidates == []


def test_no_federation_block_on_target_defaults_to_tenant_private() -> None:
    """Missing federation block → safe-default tenant_private → no match."""
    src = _envelope_with_units(
        "doc_src",
        [{"unit_id": "u1", "text_hash": _SHARED_HASH}],
        federation_policy=_ALLOW_TRUSTED_EXCHANGE,
    )
    tgt = _envelope_with_units(
        "doc_tgt",
        [{"unit_id": "u2", "text_hash": _SHARED_HASH}],
        federation_policy=None,  # no block at all
    )
    out = cross_tenant_link(src, [tgt])
    assert out.candidates == []


# ---------------------------------------------------------------------------
# Three-target case — mixed
# ---------------------------------------------------------------------------


def test_three_targets_mixed_only_permitted_survive() -> None:
    src = _envelope_with_units(
        "doc_src",
        [{"unit_id": "u1", "text_hash": _SHARED_HASH}],
        federation_policy=_ALLOW_TRUSTED_EXCHANGE,
    )
    tgt_allow = _envelope_with_units(
        "doc_tgt_allow",
        [{"unit_id": "u2", "text_hash": _SHARED_HASH}],
        federation_policy=_ALLOW_TRUSTED_EXCHANGE,
    )
    tgt_deny = _envelope_with_units(
        "doc_tgt_deny",
        [{"unit_id": "u3", "text_hash": _SHARED_HASH}],
        federation_policy=_DENY_TENANT_PRIVATE,
    )
    tgt_no_block = _envelope_with_units(
        "doc_tgt_no_block",
        [{"unit_id": "u4", "text_hash": _SHARED_HASH}],
        federation_policy=None,
    )
    out = cross_tenant_link(src, [tgt_allow, tgt_deny, tgt_no_block])
    surviving = {c.target_document_id for c in out.candidates}
    assert surviving == {"doc_tgt_allow"}


# ---------------------------------------------------------------------------
# Validation — envelopes carrying the result still pass validate_envelope
# ---------------------------------------------------------------------------


def test_source_envelope_with_federation_block_validates() -> None:
    src = _envelope_with_units(
        "doc_src",
        [{"unit_id": "u1", "text_hash": _SHARED_HASH}],
        federation_policy=_ALLOW_TRUSTED_EXCHANGE,
    )
    result = validate_envelope(src)
    assert result.valid, (
        f"source envelope with federation block should validate: "
        f"{[(i.path, i.message) for i in result.errors()]}"
    )
