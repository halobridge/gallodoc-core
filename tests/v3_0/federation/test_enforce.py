"""Codex 08 — federation/enforce.py: apply policy to linker output."""

from __future__ import annotations

from gallodoc.federation.enforce import (
    apply_federation_policy,
    build_matching_receipts,
)
from gallodoc.linking.linker import LinkerOutput, RelationshipCandidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _envelope(
    *,
    allowed: bool = True,
    scope: str = "trusted_exchange",
    fp_share: bool = True,
    emb_share: bool = True,
    requires_review: bool = False,
    permitted_rel_types: list[str] | None = None,
    tenant_hash: str = "sha256:" + "0" * 64,
) -> dict:
    return {
        "schema_version": "gallodoc-core/v3",
        "federation": {
            "schema_version": "gallodoc.federation.v3.0",
            "tenant_id_hash": tenant_hash,
            "cross_tenant_policy": {
                "allowed": allowed,
                "sharing_scope": scope,
                "raw_data_visible": False,
                "fingerprint_sharing_allowed": fp_share,
                "embedding_sharing_allowed": emb_share,
                "requires_review": requires_review,
                "permitted_relationship_types": permitted_rel_types or [],
            },
        },
    }


def _candidate(
    *,
    relationship_id: str = "rel_abc123",
    relationship_type: str = "duplicate_of",
    evidence_types_and_weights: list[tuple[str, float]] | None = None,
) -> RelationshipCandidate:
    evidence_types_and_weights = evidence_types_and_weights or [
        ("shared_text_hash", 0.95)
    ]
    return RelationshipCandidate(
        relationship_id=relationship_id,
        source_document_id="doc-src",
        target_document_id="doc-tgt",
        relationship_type=relationship_type,
        reason_code="test",
        status="suggested",
        discovered_by="gallodoc-linker/3.0.0",
        confidence=min(1.0, sum(w for _, w in evidence_types_and_weights)),
        relationship_evidence=[
            {
                "evidence_type": et,
                "weight": w,
                "source_locator": f"src.{et}",
                "candidate_locator": f"tgt.{et}",
            }
            for et, w in evidence_types_and_weights
        ],
        created_at="2026-05-17T00:00:00Z",
    )


def _output(candidates: list[RelationshipCandidate]) -> LinkerOutput:
    return LinkerOutput(source_document_id="doc-src", candidates=list(candidates))


# ---------------------------------------------------------------------------
# apply_federation_policy — gating
# ---------------------------------------------------------------------------


def test_both_sides_allowed_trusted_exchange_all_candidates_survive() -> None:
    src = _envelope(scope="trusted_exchange")
    tgt = _envelope(scope="trusted_exchange")
    out = _output([_candidate()])
    result = apply_federation_policy(src, tgt, out)
    assert len(result.candidates) == 1


def test_one_side_disabled_drops_all_candidates() -> None:
    src = _envelope(scope="disabled")
    tgt = _envelope(scope="trusted_exchange")
    out = _output([_candidate()])
    result = apply_federation_policy(src, tgt, out)
    assert result.candidates == []


def test_one_side_tenant_private_drops_all_candidates() -> None:
    src = _envelope(scope="tenant_private")
    tgt = _envelope(scope="trusted_exchange")
    out = _output([_candidate()])
    result = apply_federation_policy(src, tgt, out)
    assert result.candidates == []


def test_not_allowed_on_either_side_drops_all_candidates() -> None:
    src = _envelope(allowed=False, scope="trusted_exchange")
    tgt = _envelope(allowed=True, scope="trusted_exchange")
    out = _output([_candidate()])
    result = apply_federation_policy(src, tgt, out)
    assert result.candidates == []


# ---------------------------------------------------------------------------
# apply_federation_policy — signal admissibility per scope
# ---------------------------------------------------------------------------


def test_fingerprint_only_admits_hash_signal_filters_semantic_intent() -> None:
    """Under fingerprint_only, semantic_intent_match is filtered out."""
    src = _envelope(scope="fingerprint_only")
    tgt = _envelope(scope="fingerprint_only")
    # Candidate with only semantic_intent_match evidence → no admissible
    # signals → dropped
    semantic_only_cand = _candidate(
        relationship_id="rel_only_semantic",
        evidence_types_and_weights=[("semantic_intent_match", 0.60)],
    )
    # Candidate with hash-based evidence → admissible
    hash_cand = _candidate(
        relationship_id="rel_hash",
        evidence_types_and_weights=[("shared_text_hash", 0.95)],
    )
    out = _output([semantic_only_cand, hash_cand])
    result = apply_federation_policy(src, tgt, out)
    surviving_ids = {c.relationship_id for c in result.candidates}
    assert surviving_ids == {"rel_hash"}


def test_fingerprint_only_strips_semantic_signals_from_mixed_evidence() -> None:
    """A mixed-evidence candidate keeps only admissible entries; confidence is recomputed."""
    src = _envelope(scope="fingerprint_only")
    tgt = _envelope(scope="fingerprint_only")
    mixed = _candidate(
        evidence_types_and_weights=[
            ("shared_text_hash", 0.95),
            ("semantic_intent_match", 0.60),  # filtered
            ("shared_semantic_role", 0.10),  # filtered
        ],
    )
    result = apply_federation_policy(src, tgt, _output([mixed]))
    assert len(result.candidates) == 1
    surviving = result.candidates[0]
    assert len(surviving.relationship_evidence) == 1
    assert surviving.relationship_evidence[0]["evidence_type"] == "shared_text_hash"
    assert surviving.confidence == 0.95  # only the text-hash weight contributes


def test_semantic_only_admits_embedding_signals_filters_text_hash() -> None:
    src = _envelope(scope="semantic_only")
    tgt = _envelope(scope="semantic_only")
    hash_only_cand = _candidate(
        relationship_id="rel_hash_only",
        evidence_types_and_weights=[("shared_text_hash", 0.95)],
    )
    semantic_cand = _candidate(
        relationship_id="rel_semantic",
        evidence_types_and_weights=[("semantic_intent_match", 0.60)],
    )
    out = _output([hash_only_cand, semantic_cand])
    result = apply_federation_policy(src, tgt, out)
    surviving_ids = {c.relationship_id for c in result.candidates}
    assert surviving_ids == {"rel_semantic"}


def test_trusted_exchange_admits_all_signals() -> None:
    src = _envelope(scope="trusted_exchange")
    tgt = _envelope(scope="trusted_exchange")
    cand = _candidate(
        evidence_types_and_weights=[
            ("shared_text_hash", 0.95),
            ("semantic_intent_match", 0.60),
            ("shared_evidence_ref", 0.60),
            ("shared_semantic_role", 0.10),
        ],
    )
    result = apply_federation_policy(src, tgt, _output([cand]))
    assert len(result.candidates) == 1
    # All 4 evidence entries survived
    assert len(result.candidates[0].relationship_evidence) == 4


# ---------------------------------------------------------------------------
# apply_federation_policy — permitted_relationship_types
# ---------------------------------------------------------------------------


def test_permitted_relationship_types_allowlist_filters_out_others() -> None:
    src = _envelope(scope="trusted_exchange", permitted_rel_types=["same_customer"])
    tgt = _envelope(scope="trusted_exchange")
    cand_in = _candidate(
        relationship_id="rel_same_customer",
        relationship_type="same_customer",
    )
    cand_out = _candidate(
        relationship_id="rel_duplicate",
        relationship_type="duplicate_of",
    )
    result = apply_federation_policy(src, tgt, _output([cand_in, cand_out]))
    surviving_ids = {c.relationship_id for c in result.candidates}
    assert surviving_ids == {"rel_same_customer"}


def test_permitted_relationship_types_empty_on_both_sides_no_restriction() -> None:
    src = _envelope(scope="trusted_exchange", permitted_rel_types=[])
    tgt = _envelope(scope="trusted_exchange", permitted_rel_types=[])
    cand_a = _candidate(relationship_id="rel_a", relationship_type="duplicate_of")
    cand_b = _candidate(relationship_id="rel_b", relationship_type="same_customer")
    result = apply_federation_policy(src, tgt, _output([cand_a, cand_b]))
    surviving_ids = {c.relationship_id for c in result.candidates}
    assert surviving_ids == {"rel_a", "rel_b"}


# ---------------------------------------------------------------------------
# build_matching_receipts
# ---------------------------------------------------------------------------


def test_build_matching_receipts_raw_data_exposed_always_false() -> None:
    src = _envelope(scope="fingerprint_only", tenant_hash="sha256:" + "a" * 64)
    tgt = _envelope(scope="trusted_exchange", tenant_hash="sha256:" + "b" * 64)
    cand = _candidate()
    receipts = build_matching_receipts(src, tgt, _output([cand]))
    assert len(receipts) == 1
    r = receipts[0]
    assert r["raw_data_exposed"] is False
    # method reflects effective (most-restrictive) scope
    assert r["method"] == "fingerprint_only"
    assert r["source_profile_ref"] == "tenant://sha256:" + "a" * 64
    assert r["target_profile_ref"] == "tenant://sha256:" + "b" * 64
    assert r["matching_id"] == "match_" + cand.relationship_id
    assert 0.0 <= r["confidence"] <= 1.0
    assert r["created_at"] == cand.created_at


def test_build_matching_receipts_empty_when_policy_denies() -> None:
    src = _envelope(scope="tenant_private")
    tgt = _envelope(scope="trusted_exchange")
    receipts = build_matching_receipts(src, tgt, _output([_candidate()]))
    assert receipts == []


def test_build_matching_receipts_one_per_candidate() -> None:
    src = _envelope(scope="trusted_exchange")
    tgt = _envelope(scope="trusted_exchange")
    candidates = [
        _candidate(relationship_id=f"rel_{i:03d}")
        for i in range(3)
    ]
    receipts = build_matching_receipts(src, tgt, _output(candidates))
    assert len(receipts) == 3
    matching_ids = {r["matching_id"] for r in receipts}
    assert matching_ids == {
        "match_rel_000",
        "match_rel_001",
        "match_rel_002",
    }
    for r in receipts:
        assert r["raw_data_exposed"] is False
