"""Apply federation policy to linker output.

Codex 04's linker extracts signals and emits ``relationship_evidence[]``
entries with ``evidence_type`` strings via
``gallodoc.linking.evidence.SIGNAL_TO_EVIDENCE_TYPE``. This module:

1. Computes the most-restrictive-intersection policy from two envelopes
   (via :mod:`gallodoc.federation.policy`).
2. Filters each candidate's ``relationship_evidence[]`` against the
   admissibility matrix for the effective ``sharing_scope``.
3. Drops candidates whose ``relationship_type`` falls outside
   ``permitted_relationship_types`` (when non-empty).
4. Recomputes the candidate's confidence from admissible-only signals.
5. Builds ``federation.matching_receipts[]`` entries with
   ``raw_data_exposed: False`` for each surviving candidate.
"""

from __future__ import annotations

from typing import Any

from gallodoc.federation.policy import (
    CrossTenantPolicy,
    intersect,
    is_cross_tenant_match_permitted,
)
from gallodoc.linking.evidence import SIGNAL_TO_EVIDENCE_TYPE
from gallodoc.linking.linker import LinkerOutput, RelationshipCandidate


# Signal admissibility matrix — keys are the ``evidence_type`` strings that
# ``gallodoc.linking.evidence.build_evidence`` actually emits (the renamed
# names from SIGNAL_TO_EVIDENCE_TYPE), so this table can look up entries
# directly from each ``relationship_evidence[]`` element.
#
# For each evidence_type, the inner dict says whether the evidence
# contributes under each of the three "open" sharing scopes. Under
# ``tenant_private`` or ``disabled``, no evidence is admissible at all
# (handled separately via ``is_cross_tenant_match_permitted``).
#
# - ``fingerprint_only``: hash-based / ID-based signals only.
# - ``semantic_only``: embedding-profile signals only.
# - ``trusted_exchange``: all signals.
_SIGNAL_ADMISSIBILITY: dict[str, dict[str, bool]] = {
    # Hash-based signals
    "shared_text_hash":                 {"fingerprint_only": True,  "semantic_only": False, "trusted_exchange": True},
    "shared_claim_id":                  {"fingerprint_only": True,  "semantic_only": False, "trusted_exchange": True},
    "shared_projection_hash":           {"fingerprint_only": True,  "semantic_only": False, "trusted_exchange": True},
    "shared_source_record_id":          {"fingerprint_only": True,  "semantic_only": False, "trusted_exchange": True},
    "shared_relationship_value_hash":   {"fingerprint_only": True,  "semantic_only": False, "trusted_exchange": True},
    # Embedding-profile signals
    "shared_evidence_ref":              {"fingerprint_only": False, "semantic_only": True,  "trusted_exchange": True},
    "semantic_intent_match":            {"fingerprint_only": False, "semantic_only": True,  "trusted_exchange": True},
    "shared_semantic_role":             {"fingerprint_only": False, "semantic_only": True,  "trusted_exchange": True},
}


def _evidence_type_admissible(evidence_type: str, scope: str) -> bool:
    """True iff an evidence entry of this type contributes under this scope."""
    row = _SIGNAL_ADMISSIBILITY.get(evidence_type)
    if row is None:
        # Unknown evidence_type → treat as not admissible (conservative).
        return False
    return row.get(scope, False)


def apply_federation_policy(
    source_envelope: dict[str, Any],
    target_envelope: dict[str, Any],
    output: LinkerOutput,
) -> LinkerOutput:
    """Filter a :class:`LinkerOutput` per the intersected federation policy.

    Returns a NEW LinkerOutput; the input is not mutated.

    Candidates are dropped when:
      - Either side's policy is ``disabled`` / ``tenant_private`` (no
        cross-tenant match permitted at all)
      - All of the candidate's evidence entries are inadmissible under
        the effective ``sharing_scope``
      - The candidate's ``relationship_type`` is not in the (non-empty)
        ``permitted_relationship_types`` allowlist

    Surviving candidates have:
      - ``relationship_evidence[]`` filtered to admissible entries only
      - ``confidence`` recomputed as the sum of admissible weights (capped at 1.0)
      - the original ``relationship_id``, ``created_at``, etc. preserved
    """
    src_policy = CrossTenantPolicy.from_envelope(source_envelope)
    tgt_policy = CrossTenantPolicy.from_envelope(target_envelope)
    effective = intersect(src_policy, tgt_policy)

    if not is_cross_tenant_match_permitted(effective):
        return LinkerOutput(
            source_document_id=output.source_document_id,
            candidates=[],
        )

    scope = effective.sharing_scope
    filtered: list[RelationshipCandidate] = []
    for c in output.candidates:
        # Filter the candidate's evidence to admissible entries only.
        admissible_evidence: list[dict[str, Any]] = []
        for ev in c.relationship_evidence:
            ev_type = ev.get("evidence_type", "") if isinstance(ev, dict) else ""
            if _evidence_type_admissible(ev_type, scope):
                admissible_evidence.append(ev)
        if not admissible_evidence:
            continue  # no admissible evidence → drop candidate

        # permitted_relationship_types allowlist (when non-empty).
        if (
            effective.permitted_relationship_types
            and c.relationship_type not in effective.permitted_relationship_types
        ):
            continue

        # Recompute confidence from admissible signals only.
        new_confidence = min(
            1.0,
            sum(float(ev.get("weight", 0.0)) for ev in admissible_evidence),
        )

        filtered.append(
            RelationshipCandidate(
                relationship_id=c.relationship_id,
                source_document_id=c.source_document_id,
                target_document_id=c.target_document_id,
                relationship_type=c.relationship_type,
                reason_code=c.reason_code,
                status=c.status,
                discovered_by=c.discovered_by,
                confidence=new_confidence,
                relationship_evidence=admissible_evidence,
                semantic_intent=c.semantic_intent,
                created_at=c.created_at,
            )
        )

    return LinkerOutput(
        source_document_id=output.source_document_id,
        candidates=filtered,
    )


def build_matching_receipts(
    source_envelope: dict[str, Any],
    target_envelope: dict[str, Any],
    output: LinkerOutput,
) -> list[dict[str, Any]]:
    """Build ``federation.matching_receipts[]`` entries.

    One receipt per surviving candidate after policy enforcement. ``method``
    reflects the effective ``sharing_scope`` (mapped to the receipt method
    enum: ``fingerprint_only | semantic_only | trusted_exchange``).
    ``raw_data_exposed`` is always ``False`` — Rule 5.

    Returns an empty list when the intersected policy does not permit
    cross-tenant matching.
    """
    src_policy = CrossTenantPolicy.from_envelope(source_envelope)
    tgt_policy = CrossTenantPolicy.from_envelope(target_envelope)
    effective = intersect(src_policy, tgt_policy)
    if not is_cross_tenant_match_permitted(effective):
        return []

    src_tenant_hash = (source_envelope.get("federation") or {}).get(
        "tenant_id_hash", "unknown"
    )
    tgt_tenant_hash = (target_envelope.get("federation") or {}).get(
        "tenant_id_hash", "unknown"
    )

    # Map effective sharing_scope → matching_receipt.method. The three
    # open scopes map directly; any unexpected value falls back to the
    # most restrictive open scope.
    method = (
        effective.sharing_scope
        if effective.sharing_scope
        in ("fingerprint_only", "semantic_only", "trusted_exchange")
        else "fingerprint_only"
    )

    receipts: list[dict[str, Any]] = []
    for c in output.candidates:
        receipts.append(
            {
                "matching_id": f"match_{c.relationship_id}",
                "source_profile_ref": f"tenant://{src_tenant_hash}",
                "target_profile_ref": f"tenant://{tgt_tenant_hash}",
                "method": method,
                "confidence": c.confidence,
                "policy_outcome_ref": "",  # production: refers to policy_governance.policy_outcomes[]
                "raw_data_exposed": False,  # Rule 5 — must be false in v3.0
                "created_at": c.created_at,
            }
        )
    return receipts


__all__ = [
    "SIGNAL_TO_EVIDENCE_TYPE",  # re-export for convenience
    "apply_federation_policy",
    "build_matching_receipts",
]
