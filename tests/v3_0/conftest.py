"""Shared fixtures + helper for v3_0 tests."""

from __future__ import annotations

import copy
from pathlib import Path


# Minimal-but-valid v3 envelope. Carries all 18 required top-level sections
# at safe defaults. Tests mutate this freely; we always hand out a deep copy.
_MINIMAL_V3: dict = {
    "schema_version": "gallodoc-core/v3",
    "identity": {
        "gallodoc_id": "doc-v3-minimal-0001",
        "schema_version": "gallodoc-core/v3",
        "title": "Minimal v3 envelope (synthetic)",
        "document_type": "test_fixture",
        "mime_type": "application/octet-stream",
        "created_at": "2026-05-16T00:00:00+00:00",
        "content_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    },
    "source": {
        "source_system": "synthetic",
        "source_kind": "test_fixture",
        "ingested_at": "2026-05-16T00:00:00+00:00",
        "readiness_status": "ready",
    },
    "purpose": {
        "primary_intent": "test",
        "workflow_intent": "test",
    },
    "lifecycle": {
        "available": False,
        "current_status": "",
        "stages": [],
    },
    "activity": {
        "available": False,
        "event_count": 0,
        "counts_by_type": {},
        "latest_events": [],
    },
    "relationships": {
        "schema_version": "gallodoc.relationships.v3.0",
        "relationships": [],
        "relationship_evidence": [],
        "relationship_decisions": [],
    },
    "evidence": {"count": 0, "refs": []},
    "validations": {
        "contradictions": [],
        "packet_findings": [],
        "model_disagreements": [],
    },
    "security": {
        "phi_detected": False,
        "phi_categories": [],
        "phi_risk_level": "none",
        "encrypted": False,
        "encryption_backend": None,
        "encryption_key_id": None,
        "encrypted_fields": [],
        "masked_fields": [],
        "redaction_policy": None,
        "raw_export_allowed": True,
        "encryption_policy_status": "not_required",
        "last_phi_scan_at": None,
        "last_encrypted_at": None,
    },
    "exports": [],
    "extensions": {},
    "ai_usage": {
        "summary": {
            "total_runs": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "estimated_total_cost": 0.0,
            "currency": "USD",
        },
        "runs": [],
    },
    "gallounits": {
        "unit_strategy": "gallounit_v1",
        "units": [],
    },
    "certification": {
        "status": "none",
        "certification_type": "none",
    },
    "gstp": {
        "package_id": "",
        "package_type": "none",
        "status": "not_created",
    },
    "truth_ledger": {
        "available": False,
        "truth_state": "uncertified",
        "claims": [],
        "events": [],
    },
    "trust": {
        "schema_version": "gallodoc.trust.v3.0",
        "components": [],
        "drivers": [],
        "blockers": [],
        "warnings": [],
        "decision_gates": [],
        "policy_outcomes": [],
        "action_recommendations": [],
        "decision_receipts": [],
    },
}


def minimal_v3_envelope() -> dict:
    """Return a fresh deep copy of the minimal-but-valid v3 envelope."""
    return copy.deepcopy(_MINIMAL_V3)


# ---------------------------------------------------------------------------
# Re-export the package-level examples directory so v3_0 tests can locate
# example files without re-implementing path discovery.
# ---------------------------------------------------------------------------

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLES_DIR = PACKAGE_ROOT / "examples"
