---
title: "GalloDoc 1.1 — Governing AI Execution"
version: "1.1"
status: release-candidate
audience: "AI platform teams; security reviewers; governance teams; agent infrastructure teams"
last_updated: "2026-05-02"
keywords: "AI execution governance, capability tokens, tool contracts, execution receipts, GalloDoc 1.1"
---

# Governing AI Execution

## Executive Summary

AI systems usually fail in deployed workflows for reasons that have little to do with
model intelligence. They fail because execution is not governed. A model calls
the wrong tool. An agent receives access it should not have. A prompt changes
without review. A skill performs work outside its declared boundary. A workflow
produces a result, but nobody can prove which request, permission, tool,
policy, prompt, and receipt created it.

Modern AI infrastructure has made important progress. MCP exposes tools. A2A
connects agents. Skills package repeatable work. Prompt systems define reusable
instructions. But these layers do not, by themselves, answer the most important
enterprise governance question:

What is allowed to happen?

GalloDoc 1.1 introduces execution governance for AI, tool, agent, skill, and
prompt activity on traceable documents. It adds Capability Tokens, Execution
Requests, Execution Receipts, MCP Tool Contracts, A2A Agent Contracts, Skill
Contracts, Prompt Contracts, and Delegation Policies.

The result is a governed execution loop:

requested -> validated -> executed -> recorded

Instead of asking "What happened?" after an AI incident, an enterprise can ask:
"What exactly happened, why was it allowed, which contract controlled it, and
which receipt proves the outcome?"

## The Governance Gap in AI Execution

The first generation of enterprise AI adoption focused on model selection,
prompt quality, retrieval, and workflow automation. Those matter. But they are
not sufficient for controlled operations.

An AI system is not just a model. It is an execution environment. It may call
tools, read documents, query databases, invoke APIs, delegate work to agents,
use skills, apply prompts, transform data, send messages, create exports, or
trigger business actions.

Each of those actions creates risk. The model can be accurate and the system can
still fail because an action was unauthorized, unscoped, unrecorded, or
impossible to audit.

Common failure modes include:

- Tool misuse: a tool is called with the wrong scope or at the wrong stage.
- Permission drift: an agent gains access through workflow composition rather
  than explicit grant.
- Prompt opacity: a prompt version changes and downstream behavior changes with
  it.
- Skill ambiguity: a packaged capability performs work beyond its declared
  purpose.
- Missing receipts: an action occurs, but the system cannot produce a durable
  proof object.
- Delegation sprawl: agent-to-agent chains expand without clear limits.

The deeper issue is that most AI systems treat execution as an implementation
detail. Enterprises need to treat execution as a governed object.

## Why Access Control Alone Is Not Enough

Traditional access control answers whether a user or service can reach a
resource. AI execution governance requires a more precise question: Is this
specific action, on this subject, by this actor, through this tool or agent,
under this contract, allowed for this purpose at this moment?

Role-based access control cannot fully answer that. API keys cannot answer it.
Tool registries cannot answer it. Prompt management cannot answer it. Agent
framework logs cannot answer it.

AI governance needs proof objects that bind intention, authority, constraints,
execution, and outcome.

GalloDoc 1.1 adds those proof objects directly into the document-centered
governance layer. The document is not merely data being processed. It is the
subject around which execution permission, policy, and proof are organized.

## The GalloDoc 1.1 Model

GalloDoc 1.1 is an optional additive extension to the GalloDoc Core v1
envelope. Its central block, `execution_governance`, records metadata and proof
objects for governed execution. It does not store raw prompts, raw model
responses, secrets, bearer tokens, or PHI. It records safe references, hashes,
counts, summaries, and contract metadata.

The logical object model includes:

- `GalloCapabilityToken`: an opaque grant reference that scopes allowed actions
  on a subject.
- `GalloExecutionRequest`: an intended action bound to a capability token and
  relevant contracts.
- `GalloExecutionReceipt`: a proof object that records outcome, policy decision
  summary, hashes, and execution metadata.
- `GalloMCPToolContract`: declared tool limits and resource scope metadata.
- `GalloA2AAgentContract`: agent trust metadata and capability boundaries.
- `GalloSkillContract`: declared skill purpose, scope, and risk flags.
- `GalloPromptContract`: prompt definition metadata with prompt and response
  hashes, never full prompt or response bodies.
- `GalloDelegationPolicy`: constraints on agent-to-agent delegation chains.

This creates a contract-backed system in which execution can be reasoned about
before and after it happens.

## From Tool Calls to Governed Actions

In an ungoverned AI stack, a tool call is often just an event in a log. In a
governed stack, a tool call is the result of a permissioned request.

The difference is significant. A governed action has a declared subject, actor,
purpose, capability, contract, policy decision, and receipt. It can be denied,
approved, limited, escalated, or recorded. It can be inspected later by a
reviewer who does not need to reverse-engineer the runtime.

The execution lifecycle becomes:

1. A system or agent creates an execution request.
2. The request references the document subject and intended action.
3. The request is checked against capability tokens, contracts, policies, and
   delegation limits.
4. The action is executed only if allowed.
5. The system emits an execution receipt.
6. The receipt becomes part of the document's governance history.

This turns AI execution from a best-effort runtime behavior into an auditable
control surface.

## Relationship to MCP, A2A, Skills, and Prompts

GalloDoc 1.1 does not replace tool protocols, agent protocols, skills, or
prompt management. It governs them.

MCP can expose a tool, but GalloDoc 1.1 can declare which document subject,
resource scope, and action boundary applies. A2A can connect agents, but
GalloDoc 1.1 can record agent contracts and delegation policies. Skills can
package work, but GalloDoc 1.1 can bind the skill to declared risk metadata and
allowed usage. Prompts can define intelligence, but GalloDoc 1.1 can identify
the prompt contract and preserve hashes without exposing prompt bodies.

The principle is simple: execution infrastructure enables action; GalloDoc 1.1
proves whether the action was allowed and what happened.

## Enterprise Controls Enabled

With GalloDoc 1.1, enterprises can implement controls that are difficult to
enforce with logs alone:

- Deny tool calls that lack a valid capability token.
- Require specific tool contracts for sensitive document classes.
- Block prompt contracts that are deprecated, experimental, or unapproved.
- Limit agent delegation depth.
- Require human approval before high-risk skills can execute.
- Bind execution receipts to downstream exports and audit packages.
- Compare actual execution against declared workflow purpose.
- Produce evidence for security, compliance, and customer review.

These controls are especially important in regulated, high-value, or
operationally sensitive workflows where AI is allowed to do more than generate
text.

## Privacy and Safety Design

GalloDoc 1.1 is designed to govern execution without becoming a new repository
of secrets. It uses hashes, opaque references, summaries, and contract metadata.
Open-core safety rules exclude raw prompts, raw responses, provider authorization tokens, API
secrets, PEM material, bearer strings, IP or session hashes, clinical
identifiers, and PHI in the execution governance block.

This is essential. Governance artifacts should be inspectable, exchangeable,
and durable without exposing the sensitive payloads they govern.

## Business Impact

For AI platform teams, GalloDoc 1.1 creates a durable control layer for
agentic execution. For security teams, it provides proof that actions were
permissioned and scoped. For compliance teams, it produces records that can be
reviewed without reconstructing runtime behavior. For business owners, it makes
automation accountable enough to deploy in meaningful workflows.

The strategic impact is larger than auditability. GalloDoc 1.1 gives
enterprises a way to scale AI without relying on informal trust in agents,
prompts, and tools. It turns execution into a first-class governed asset.

## Conclusion

AI does not become enterprise-grade when it becomes more fluent. It becomes
enterprise-grade when its actions are controlled, explainable, permitted, and
provable.

GalloDoc 1.1 provides that execution governance layer. Every AI action can be
requested, validated, executed, and recorded. Every tool, agent, skill, and
prompt can be tied to a contract. Every sensitive action can leave behind a
receipt.

The enterprise question changes from "What did the AI do?" to "Was this action
allowed, under which contract, with what outcome, and where is the proof?"
