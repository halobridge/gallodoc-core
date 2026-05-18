"""Fixture helpers for v3_0/projection tests.

Builds minimal v1 envelopes (for migration coverage) and re-exports the
v3 minimal envelope from the parent ``tests/v3_0/conftest.py``.
"""

from __future__ import annotations

import copy
from typing import Any

from tests.v3_0.conftest import minimal_v3_envelope  # re-exported for use by tests


# Minimal v1 envelope. Carries the bare-list `relationships` shape and
# nested `trust_score` / `trust_decision` so migration tests can assert
# on the three transforms.
_MINIMAL_V1: dict[str, Any] = {
    "schema_version": "gallodoc-core/v1",
    "identity": {
        "gallodoc_id": "doc-v1-minimal-0001",
        "title": "Minimal v1 envelope (synthetic)",
        "document_type": "test_fixture",
        "mime_type": "application/octet-stream",
        "schema_version": "gallodoc-core/v1",
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
    "relationships": [],  # v1 bare-list shape
    "evidence": {"count": 0, "refs": []},
    "validations": {"contradictions": [], "packet_findings": [], "model_disagreements": []},
    "security": {
        "phi_detected": False,
        "phi_categories": [],
        "phi_risk_level": "none",
        "encrypted": False,
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
    "gallounits": {"unit_strategy": "gallounit_v1", "units": []},
    "certification": {"status": "none", "certification_type": "none"},
    "gstp": {"package_id": "", "package_type": "none", "status": "not_created"},
    "truth_ledger": {
        "available": False,
        "truth_state": "uncertified",
        "claims": [],
        "events": [],
    },
}


def minimal_v1_envelope() -> dict[str, Any]:
    """Return a fresh deep copy of the minimal-but-shaped v1 envelope."""
    return copy.deepcopy(_MINIMAL_V1)


def v1_envelope_with_nested_trust() -> dict[str, Any]:
    """v1 envelope carrying both `trust_score` and `trust_decision`."""
    env = minimal_v1_envelope()
    env["trust_score"] = {
        "components": [
            {"name": "evidence_coverage", "score": 0.92},
            {"name": "policy_alignment", "score": 0.81},
        ],
        "drivers": [{"label": "complete evidence", "weight": 0.5}],
        "blockers": [{"label": "missing attestation", "severity": "high"}],
        "warnings": [{"label": "stale evidence", "severity": "low"}],
    }
    env["trust_decision"] = {
        "gates": [{"gate_id": "gate-1", "verdict": "pass"}],
        "policy_outcomes": [{"policy_id": "pol-1", "outcome": "allow"}],
        "action_recommendations": [{"action_id": "act-1", "verb": "review"}],
        "decision_receipts": [{"receipt_id": "rcpt-1", "decided_at": "2026-05-16T00:00:00+00:00"}],
    }
    return env


def v1_envelope_with_halobridge_block(block_name: str, content: Any = None) -> dict[str, Any]:
    """v1 envelope carrying a single `extensions.halobridge.<block_name>` payload."""
    env = minimal_v1_envelope()
    if content is None:
        content = {"any": "shape", "_demo_block": block_name}
    env["extensions"] = {"halobridge": {block_name: content}}
    return env


__all__ = [
    "minimal_v1_envelope",
    "minimal_v3_envelope",
    "v1_envelope_with_nested_trust",
    "v1_envelope_with_halobridge_block",
]
