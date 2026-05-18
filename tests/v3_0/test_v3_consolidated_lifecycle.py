"""v3 lifecycle is the v1 `lifecycle.stages[]` shape plus an optional
`lifecycle.workflow_steps[]` array carrying the v2.0 workflow_execution
per-step shape.
"""

from __future__ import annotations

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


def test_v1_lifecycle_stages_shape_validates() -> None:
    env = minimal_v3_envelope()
    env["lifecycle"] = {
        "available": True,
        "current_status": "review_complete",
        "schema_version": "document_lifecycle/v1",
        "stages": [
            {
                "stage": "ingest",
                "status": "completed",
                "actor": "system",
                "timestamp": "2026-05-16T00:00:00+00:00",
                "source": "upload_portal",
            }
        ],
    }
    result = validate_envelope(env)
    assert result.valid, f"v1 lifecycle.stages[] shape should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_lifecycle_with_optional_workflow_steps_validates() -> None:
    env = minimal_v3_envelope()
    env["lifecycle"] = {
        "available": True,
        "current_status": "review_complete",
        "stages": [
            {"stage": "ingest", "status": "completed"},
            {"stage": "review", "status": "completed"},
        ],
        "workflow_steps": [
            {
                "step_id": "ws-001",
                "workflow_run_id": "wr-001",
                "step_name": "ingest",
                "step_type": "ingest",
                "status": "completed",
                "input_hash": "sha256:" + "i" * 64,
                "output_hash": "sha256:" + "o" * 64,
                "duration_ms": 1200,
                "error_summary": "",
            }
        ],
    }
    result = validate_envelope(env)
    assert result.valid, f"lifecycle with workflow_steps should validate: {[(i.path, i.message) for i in result.errors()]}"


def test_missing_lifecycle_fails_required_check() -> None:
    env = minimal_v3_envelope()
    env.pop("lifecycle")
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i for i in result.errors() if i.path == "lifecycle" and "required field missing" in i.message
    ]
    assert matching


def test_lifecycle_with_v20_workflow_step_field_types_pass() -> None:
    """The v3 workflow_steps[] shape allows the same fields as v2.0
    workflow_execution.workflow_steps[]. Per-step hashes are optional."""
    env = minimal_v3_envelope()
    env["lifecycle"]["workflow_steps"] = [
        {"step_id": "ws-001", "step_name": "extract", "step_type": "extract", "status": "completed"}
    ]
    result = validate_envelope(env)
    assert result.valid
