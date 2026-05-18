"""Relationship-type catalog mapping signal combinations to v2.0 enum.

Documented in ``docs/specs/gallodoc-core-v3-linker.md`` §4. The catalog
maps signal patterns (and ``semantic_intent`` values per Decision 5) to
v2.0 ``relationship_type`` enum values plus a ``reason_code``.
"""

from __future__ import annotations

from typing import Any

from gallodoc.linking.scoring import ScoredCandidate


# v2.0 relationship_type enum the validator accepts (from
# validation/__init__.py `_validate_v20_field_ranges` for
# `document_relationships`).
ALLOWED_RELATIONSHIP_TYPES: frozenset[str] = frozenset({
    "duplicate_of", "version_of", "supersedes", "belongs_to", "supports",
    "contradicts", "same_claim", "same_patient", "same_customer",
    "same_contract", "same_invoice", "derived_from", "related_to",
})


# semantic_intent vocabulary maps to specific v2.0 enums + a reason_code.
# Decision 5 — intent describes what a relationship MEANS; role describes
# what a unit IS. Documented in
# ``docs/specs/gallodoc-semantic-intent-v3.md`` §3.
SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE: dict[str, tuple[str, str]] = {
    "invoice_to_employee_approver":   ("related_to",   "invoice_to_employee_approver"),
    "contract_supersedes_contract":   ("supersedes",   "contract_supersedes_contract"),
    "patient_to_consent_record":      ("belongs_to",   "patient_to_consent_record"),
    "claim_to_supporting_document":   ("supports",     "claim_to_supporting_document"),
    "case_to_case_continuation":      ("derived_from", "case_to_case_continuation"),
    "attachment_to_parent_document":  ("belongs_to",   "attachment_to_parent_document"),
}


def classify(
    scored: ScoredCandidate,
    source: dict[str, Any] | None = None,
    candidate: dict[str, Any] | None = None,
) -> tuple[str, str | None]:
    """Map a scored candidate to ``(relationship_type, reason_code)``.

    Returns the v2.0 enum value and an optional reason_code. Priority
    order (highest first):

      1. ``semantic_intent_match`` — explicit intent wins (Decision 5).
      2. ``claim_id_match`` → ``same_claim``.
      3. ``text_hash_match`` → ``duplicate_of`` (same canonical text).
      4. ``source_record_id_match`` → ``duplicate_of`` (same external record).
      5. ``projection_hash_match`` → ``derived_from``.
      6. (default) → ``related_to``.

    Unknown ``semantic_intent`` values default to ``related_to`` with the
    intent value carried in ``reason_code`` so consumers can still see
    the author's stated intent.
    """
    signal_names = {s.name for s in scored.signals}

    # 1. semantic_intent wins (Decision 5)
    if "semantic_intent_match" in signal_names:
        for s in scored.signals:
            if s.name == "semantic_intent_match":
                # Locator format: "gallounits.units[].semantic_intent=<intent>"
                intent = s.source_locator.split("semantic_intent=", 1)[-1]
                mapping = SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE.get(intent)
                if mapping:
                    return mapping
                # Unknown intent — default to related_to with the intent
                # value as reason_code.
                return ("related_to", intent)

    # 2. claim_id match → same_claim
    if "claim_id_match" in signal_names:
        return ("same_claim", "shared_canonical_claim")

    # 3. text_hash match → duplicate_of
    if "text_hash_match" in signal_names:
        return ("duplicate_of", "shared_canonical_text")

    # 4. source_record_id match → duplicate_of
    if "source_record_id_match" in signal_names:
        return ("duplicate_of", "shared_source_record_id")

    # 5. projection_hash match → derived_from
    if "projection_hash_match" in signal_names:
        return ("derived_from", "shared_tokenization_stable_content")

    # 6. default
    return ("related_to", None)


__all__ = [
    "ALLOWED_RELATIONSHIP_TYPES",
    "SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE",
    "classify",
]
