"""Canonical forbidden-key sets used by the v3 projector, migrator, and validator.

Imported by:
  - gallodoc.validation (banned extensions check)
  - gallodoc.projection.projector (strip targets)
  - gallodoc.projection.migrator (promote targets)
  - gallodoc.projection.safety (leak assertions)
"""

from __future__ import annotations


# The 13 v1.2–v1.6 compliance block names that must live at top level in v3,
# never under extensions.halobridge.<name>. Plus federation, which is v3-new
# and is only valid at top level (Decision 4).
EXTENSIONS_HALOBRIDGE_BANNED: frozenset[str] = frozenset({
    "consent_ledger",
    "chain_of_custody",
    "human_decisions",
    "attestations",
    "redaction_manifest",
    "evidence_quality",
    "data_residency",
    "training_permissions",
    "model_risk",
    "retention_status",
    "agent_observability",
    "trust_decision",
    "agent_supply_chain_security",
    "federation",  # Decision 4 — federation is v3-new; only valid at top level
})

# The 13 v1.2–v1.6 block names ONLY (no federation). Used by the migration
# helper's promotion step — federation cannot be promoted FROM extensions
# because it's v3-new and shouldn't exist there in any v1.x envelope.
V12_V16_COMPLIANCE_BLOCKS: frozenset[str] = EXTENSIONS_HALOBRIDGE_BANNED - {"federation"}


__all__ = ["EXTENSIONS_HALOBRIDGE_BANNED", "V12_V16_COMPLIANCE_BLOCKS"]
