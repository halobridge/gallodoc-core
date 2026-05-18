# GalloDoc Compute Trace — v2.0

**Schema slug:** `gallodoc.compute_trace.v2.0`
**Top-level key:** `compute_trace` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#10-compute_trace)

A unified, vendor-neutral spans/metrics/logs model for AI calls, tool
calls, retrieval, policy evaluations, scanners, sandboxes, exports, and
API calls. Designed to be compatible with the
[OpenTelemetry](https://opentelemetry.io/) semantic conventions for
traces, metrics, and logs so traces can be exported to standard backends
without GalloDoc consumers depending on any specific vendor.

`agent_observability` (v1.4) remains the AI-specific lens; `compute_trace`
unifies the cross-cutting view across AI, tools, scanners, and workflows.

## Shape

```json
{
  "schema_version": "gallodoc.compute_trace.v2.0",
  "spans": [],
  "metrics": [],
  "logs": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `Span`   | `span_id`, `parent_span_id`, `trace_id`, `span_name`, `span_type` (`llm_call`/`tool_call`/`retrieval`/`policy_eval`/`scanner`/`sandbox`/`export`/`api_call`), `started_at`, `ended_at`, `duration_ms`, `status`, `input_hash`, `output_hash`, `error_summary`, `linked_receipt_refs[]`. |
| `Metric` | `metric_id`, `trace_id`, `name`, `value`, `unit`, `tags_summary`, `recorded_at`. |
| `Log`    | `log_id`, `trace_id`, `level`, `event_name`, `message_summary`, `timestamp`. |

## Privacy invariants

- No raw logs with PHI or secrets. Forbidden keys include `raw_log`,
  `log_body`, `raw_message`, `raw_metric_values`. Logs and metrics
  carry summaries and hashes only.
- v1.4 `agent_observability` traces, model verifications, skill scans,
  and workflow steps all project into this block.

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_compute_trace.json`](../../examples/v2_0/gallodoc_compute_trace.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
