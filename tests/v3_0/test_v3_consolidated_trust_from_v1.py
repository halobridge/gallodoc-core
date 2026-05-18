"""v3 flat trust block accepts v1 trust_score-shaped + v1.5 trust_decision-shaped
data when manually flattened.

The migration helper that automates the projection ships in prompt 02.
This test confirms the *target* shape — a hand-flattened v3 trust block
that mirrors what the helper will produce — validates under the v3
validator.
"""

from __future__ import annotations

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


def test_flat_trust_with_v1_and_v15_shaped_data_validates() -> None:
    env = minimal_v3_envelope()
    env["trust"] = {
        "schema_version": "gallodoc.trust.v3.0",
        # Components[] from v1.5 trust_scores[] (v3 hoists the per-subject
        # score breakdown into a flat components array). Item shape ported
        # verbatim from gallodoc-core-v1.schema.json:1044-1156.
        "components": [
            {
                "score_id": "ts-001",
                "subject_type": "document",
                "subject_id": "doc-v3-minimal-0001",
                "score": 85.0,
                "grade": "B",
                "status": "trusted",
                "calculated_at": "2026-05-16T00:00:00+00:00",
                "policy_version": "trust_policy/v1",
                "scoring_profile": "default",
                "components": {
                    "evidence_quality": {"score": 88.0, "explanation": "good"},
                    "lifecycle_completeness": {"score": 90.0, "explanation": "complete"},
                    "security_posture": {"score": 85.0, "explanation": "encrypted"},
                    "execution_governance": {"score": 80.0, "explanation": "policy-gated"},
                    "consent_custody_attestation": {"score": 82.0, "explanation": "attested"},
                    "residency_training_model_risk": {"score": 84.0, "explanation": "low risk"},
                    "agent_observability": {"score": 86.0, "explanation": "traced"},
                    "human_review": {"score": 88.0, "explanation": "reviewed"},
                },
                "drivers": ["evidence_strong"],
                "blockers": [],
                "warnings": [],
                "explanation_summary": "All gates passed.",
            }
        ],
        # v1 trust_score top-level drivers / blockers / warnings hoisted flat.
        "drivers": ["evidence_strong", "lifecycle_complete"],
        "blockers": [],
        "warnings": [],
        # v1.5 trust_decision sub-arrays hoisted flat.
        "decision_gates": [
            {
                "gate_id": "g-001",
                "gate_name": "release_to_certifier",
                "action": "export",
                "subject_type": "document",
                "subject_id": "doc-v3-minimal-0001",
                "decision": "allow",
                "evaluated_at": "2026-05-16T00:00:00+00:00",
            }
        ],
        "policy_outcomes": [
            {
                "outcome_id": "po-001",
                "policy_name": "export_policy",
                "policy_version": "v1",
                "decision": "allow",
                "evaluated_at": "2026-05-16T00:00:00+00:00",
            }
        ],
        "action_recommendations": [
            {
                "recommendation_id": "ar-001",
                "recommended_action": "proceed_to_export",
                "priority": "medium",
                "reason": "all gates passed",
                "created_at": "2026-05-16T00:00:00+00:00",
            }
        ],
        "decision_receipts": [
            {
                "receipt_id": "dr-001",
                "action": "export",
                "decision": "allow",
                "created_at": "2026-05-16T00:00:00+00:00",
            }
        ],
    }
    result = validate_envelope(env)
    assert result.valid, f"flat trust block with v1+v1.5 data should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_empty_flat_trust_block_validates() -> None:
    """The empty case — `trust` block present with the schema_version and
    every array empty — must validate so that envelopes that do not have
    any trust data can still meet the 18-required-section count."""
    env = minimal_v3_envelope()
    # Already empty in the minimal fixture; assert here so a future
    # accidental fixture change is caught.
    assert env["trust"]["components"] == []
    result = validate_envelope(env)
    assert result.valid
