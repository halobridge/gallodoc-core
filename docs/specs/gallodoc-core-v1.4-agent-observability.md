# GalloDoc Core v1.4 — Agent observability (optional)

**Schema slug:** `gallodoc.agent_observability.v1.4`  
**Top-level key:** `agent_observability`

## Purpose

Optional, additive metadata for **agent evaluation**, **tracing**, **observability**, and **regression safety**.  
This block captures **hashes**, **counts**, **status enums**, and **short human-readable summaries** — never raw PHI, full prompts, full model responses, hidden reasoning traces, provider authorization secrets, or internal session/IP binding material.

## Shape (summary)

The block contains parallel arrays:

- `agent_traces` — `GalloAgentTrace` rows  
- `tool_invocation_logs` — `GalloToolInvocationLog` (tool name, schema hashes, parameter hash, latency, status)  
- `retrieval_traces` — `GalloRetrievalTrace` (query hash + summary, method, counts, grade, noise flag)  
- `reasoning_summaries` — `GalloReasoningSummary` (safe rationale only)  
- `evaluation_results` — `GalloEvaluationResult`  
- `latency_cost_metrics` — `GalloLatencyCostMetric`  
- `failure_analyses` — `GalloFailureAnalysis`  
- `regression_test_results` — `GalloRegressionTestResult`  
- `escalation_decisions` — `GalloEscalationDecision`

Field names and enums align with the HaloBridge exporter; the JSON Schema allows additional properties per trace object for forward compatibility.

## Relationship to v1.1 execution governance

When execution governance receipts exist, traces may reference `execution_request_id` and `execution_receipt_id`. Observability does **not** replace receipts — it adds cross-cutting debuggability for agent pipelines.

## Forbidden content

The open-core validator rejects dangerous keys anywhere under optional compliance-style blocks, including hidden-reasoning dumps, raw retrieval chunk bodies, and raw tool parameter blobs. Use **hashes** and **redacted summaries** only.

## Example

See `examples/v1_4/gallodoc_agent_observability.json`.
