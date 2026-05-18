# GalloDoc Core v1.6 — Agent Supply Chain Security

**Schema slug:** `gallodoc.agent_supply_chain_security.v1.6`  
**Top-level key:** `agent_supply_chain_security` (optional, additive)

## Purpose

GalloDoc Core v1.6 records install, run, and delegation risk for AI agent
skills, MCP tools, prompt packs, browser agents, and executable skill bundles.

The block is designed for proof, not payload storage. It records hashes,
summaries, scanner identifiers, sandbox observations, permission decisions,
dependency review summaries, quarantine decisions, and install receipts.

It MUST NOT store raw secrets, raw PHI, executable payloads, raw source bodies,
host execution output, packet captures, raw prompts, raw responses, or hidden
reasoning traces.

## Shape

The top-level object is:

```json
{
  "schema_version": "gallodoc.agent_supply_chain_security.v1.6",
  "scans": [],
  "findings": [],
  "package_manifests": [],
  "permission_reviews": [],
  "dependency_reviews": [],
  "sandbox_observations": [],
  "llm_security_reviews": [],
  "quarantine_decisions": [],
  "install_receipts": []
}
```

## Object Types

| Object | Role |
|---|---|
| `AgentSupplyChainScan` | Scanner metadata, target object, hash inputs, sandbox posture, timestamps. |
| `AgentSupplyChainFinding` | Severity, category, safe summary, evidence hash, install-blocking flag. |
| `AgentPackageManifest` | Package type, version, publisher reference, manifest hash, bundle hash, declared capabilities. |
| `AgentPermissionReview` | Requested, approved, and denied permissions plus least-privilege status. |
| `AgentDependencyReview` | Dependency counts, lockfile hash, untrusted dependency count, summary. |
| `AgentSandboxObservation` | Isolated sandbox summary; network off by default; no host execution output. |
| `AgentLLMSecurityReview` | Prompt-pack or LLM-facing policy review using hashes and summaries only. |
| `AgentQuarantineDecision` | Quarantine/hold/release decision with reason codes and decision role. |
| `AgentInstallReceipt` | Install decision, allowed permissions, policy version, linked execution/trust/trace refs. |

## Normative Rules

- Do not execute untrusted code on the host.
- Sandbox execution, when used, is isolated and network-off by default.
- Store hashes, summaries, scanner IDs, and decision records only.
- Critical credential theft, remote code execution, or exfiltration findings
  MUST block install.
- High-risk findings require human-in-the-middle control review before install.
- Low-risk packages may be allowed with limited permissions.

## Relationship to Other Layers

- **v1.1 execution governance:** install review should reference execution
  requests and execution receipts when present.
- **v1.4 agent observability:** review traces and sandbox summaries may link to
  trace IDs.
- **v1.5 trust decision:** install gates and trust decisions can reference v1.6
  finding and receipt IDs.
- **Document lifecycle/activity:** producers should record review and install
  decisions as lifecycle/activity events in the host system.

## Public-Safety Rules

The reference validator rejects unsafe keys and unsafe string shapes under
`agent_supply_chain_security`, including raw secret fields, executable payload
fields, raw environment dumps, JWT-shaped strings, URL-like strings,
non-allowlisted email domains, and SSN-shaped literals.

## Example

See `examples/v1_6/gallodoc_agent_supply_chain_security.json`.
