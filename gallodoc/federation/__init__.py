"""GalloDoc federation — cross-tenant matching policy + enforcement.

Per Decision 4 in ``docs/v3-design/07_decisions.md``, federation is a
first-class top-level optional block in v3. This package implements the
most-restrictive-intersection-wins enforcement that the linker consults
before producing cross-tenant relationship candidates.

Spec: ``docs/specs/gallodoc-core-v3-federation.md``.
"""

from __future__ import annotations

from typing import Any

from gallodoc.federation.enforce import (
    apply_federation_policy,
    build_matching_receipts,
)
from gallodoc.federation.policy import (
    CrossTenantPolicy,
    intersect,
    is_cross_tenant_match_permitted,
)
from gallodoc.linking.linker import LinkerOutput


def cross_tenant_link(
    source_envelope: dict[str, Any],
    target_envelopes: list[dict[str, Any]],
    *,
    min_confidence: float = 0.10,
) -> LinkerOutput:
    """Run the linker with federation enforcement applied per-target.

    For each target envelope, the cross-tenant policy intersection
    determines whether the candidate survives and what signals contribute.

    The returned :class:`LinkerOutput` contains only candidates that
    survived enforcement under their respective source/target policy
    intersection. Candidates against a target whose policy denies the
    match are dropped entirely.
    """
    # Local import to avoid an import cycle when gallodoc.linking imports
    # nothing from federation (the federation package depends on linker
    # types, not the other way around).
    from gallodoc.linking import link as base_link

    raw = base_link(source_envelope, target_envelopes, min_confidence=min_confidence)

    filtered_candidates = []
    for tgt in target_envelopes:
        tgt_id = (tgt.get("identity") or {}).get("gallodoc_id")
        per_target = LinkerOutput(
            source_document_id=raw.source_document_id,
            candidates=[c for c in raw.candidates if c.target_document_id == tgt_id],
        )
        survived = apply_federation_policy(source_envelope, tgt, per_target)
        filtered_candidates.extend(survived.candidates)
    return LinkerOutput(
        source_document_id=raw.source_document_id,
        candidates=filtered_candidates,
    )


__all__ = [
    "CrossTenantPolicy",
    "apply_federation_policy",
    "build_matching_receipts",
    "cross_tenant_link",
    "intersect",
    "is_cross_tenant_match_permitted",
]
