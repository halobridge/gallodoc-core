# GalloDoc Workflow Execution — v2.0

**Schema slug:** `gallodoc.workflow_execution.v2.0`
**Top-level key:** `workflow_execution` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#8-workflow_execution)

A projection of GalloDoc lifecycle / app runs / pipeline runs into a
single representation. The v1.0 `lifecycle` block remains the
authoritative lifecycle history; this block expresses the same activity
as a structured workflow with input/output hashes per step.

## Shape

```json
{
  "schema_version": "gallodoc.workflow_execution.v2.0",
  "workflow_runs": [],
  "workflow_steps": [],
  "workflow_artifacts": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `WorkflowRun`      | `workflow_run_id`, `workflow_name`, `app_slug`, `status` (`queued`/`running`/`completed`/`failed`/`blocked`/`skipped`), `started_at`, `completed_at`, `actor_role`, `purpose`. |
| `WorkflowStep`     | `step_id`, `workflow_run_id`, `step_name`, `step_type` (`ingest`/`ocr`/`classify`/`extract`/`review`/`verify`/`export`/`scan`/`notify`), `status`, `input_hash`, `output_hash`, `duration_ms`, `error_summary`. |
| `WorkflowArtifact` | `artifact_id`, `workflow_run_id`, `artifact_ref`, `artifact_family`, `created_at`. |

## Privacy invariants

- Step inputs and outputs are stored as hashes; raw payloads, raw
  inputs, raw outputs, raw stack traces never ship. Forbidden keys
  include `raw_input`, `raw_output`, `input_payload`, `output_payload`,
  `stack_trace`, `raw_stack_trace` (validator rejects these).
- `error_summary` is a sanitized human-readable string, never a stack
  trace with payload data.
- The block is a *projection* of lifecycle events; existing v1.0
  lifecycle artifacts remain authoritative.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_workflow_execution.json`](../../examples/v2_0/gallodoc_workflow_execution.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
