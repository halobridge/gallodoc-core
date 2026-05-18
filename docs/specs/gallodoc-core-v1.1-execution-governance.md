# GalloDoc Core v1.1 — Execution Governance (optional extension)

## Theme

- **GalloDoc 1.0** — traceable documents (identity, lifecycle, evidence, security posture, AI usage summaries, GalloUnits, certification, GSTP, Truth Ledger).
- **GalloDoc 1.1** — governed AI, tool, MCP, agent, skill, and prompt **execution** on those documents, using **proof objects** only.

This extension is **additive**. Valid v1.0 envelopes remain valid without `execution_governance`.

## Top-level block

Optional key: `execution_governance` (object).

Required when present:

- `schema_version` — must be exactly `gallodoc.execution_governance.v1.1`.

Recommended housekeeping fields (strings):

- `gallodoc_schema_version` — HaloBridge / exporter lineage.
- `execution_governance_version` — semantic version of the governance bundle.

## Object types (logical)

| Concept | Role |
|--------|------|
| **GalloCapabilityToken** | Opaque grant reference (`token_id`); scopes actions on a subject. |
| **GalloExecutionRequest** | Intended action bound to contracts / token (`request_id`). |
| **GalloExecutionReceipt** | **Proof** — outcome, policy decision summary, hashes; no bodies. |
| **GalloMCPToolContract** | Declared MCP tool limits (`tool_id`, `resource_scope` metadata only). |
| **GalloA2AAgentContract** | Agent trust metadata (`agent_id`, `capabilities_count`, …). |
| **GalloSkillContract** | Skill declaration (`skill_id`, risk flags). |
| **GalloPromptContract** | Prompt **definition** metadata plus `prompt_hash` / `response_hash` only — never prompt or response text. |
| **GalloDelegationPolicy** | Delegation chain limits (`policy_id`, `max_chain_depth`, actors as opaque strings). |

Arrays under `execution_governance` use these names:

- `capability_tokens`, `mcp_tool_contracts`, `a2a_agent_contracts`, `skill_contracts`, `prompt_contracts`, `delegation_policies`, `execution_requests`, `execution_receipts`.

## Public-safety rules (normative for open-core)

Under `execution_governance`, implementations **must not** emit:

- Raw prompts or model responses (use **`prompt_hash`** / **`response_hash`** only).
- OAuth tokens, API secrets, PEM material, vault refs, bearer material.
- **`ip_hash`**, **`session_hash`**, or JWT-shaped bearer strings.
- Clinical identifiers or other PHI in this block.

The bundled validator rejects forbidden **key names** anywhere under `execution_governance` and rejects JWT-shaped **string values**. Run `gallodoc validate <file>` before publishing.

## Schema

Structural validation is defined in `gallodoc/schema/gallodoc-core-v1.schema.json` under `properties.execution_governance`. Additional properties are allowed (`additionalProperties: true`) for forward-compatible vendor extensions, subject to the same safety rules above.

## Example

See `examples/v1_1/gallodoc_v1_1_execution_governance_reference.json`.
