# What is GalloDoc?

**Audience:** developers and compliance leads evaluating GalloDoc.
**Reading time:** ~3 minutes.
**Source:** derived from
[`docs/v3-design/03_what_is_gallodoc.md`](../../../../docs/v3-design/03_what_is_gallodoc.md).

---

## The one-line pitch

> **GalloDoc is an open standard for portable operational intelligence
> documents.**

A GalloDoc envelope is one JSON file that captures everything a downstream
auditor, reviewer, or AI/BI query engine needs to verify, reproduce, or
extend the operation that produced it. Inputs (by hash). Models (by
version). Prompts (by hash — never the raw text). Outputs. Evidence.
Reviewer decisions. Trust scores. Policy outcomes. Relationships to other
envelopes.

Every operation is the same shape. Every operation is verifiable offline.
Every operation is queryable without parsing logs.

---

## The problem

Your AI / data / agent pipeline produces operations every minute —
classifications, extractions, decisions, summaries — and nobody can prove
what any of them are based on.

The provider can't tell you which prompt produced the output. The reviewer
can't tell you which evidence the model used. The auditor can't tell you
whether the same input would produce the same answer next month. Your
compliance team is reconstructing model behavior from logs, screenshots,
and Slack messages.

When something goes wrong — a wrong claim approved, a wrong invoice
paid, a wrong patient routed — you can't replay the decision. You can't
show your work.

GalloDoc is what your system writes when it's done, so the answer to "how
did this happen" is a single file.

---

## What's in a v3 envelope

**18 required sections** (one more than v1 — the new `trust` block):

| Section | What's in it |
|---|---|
| `schema_version` | Const `gallodoc-core/v3`. |
| `identity` | Document identity + content hash. |
| `source` | Connector lineage + record origin. |
| `purpose` | Why this envelope exists. |
| `lifecycle` | Stage timeline + optional per-step input/output hashes. |
| `activity` | PII-stripped access log. |
| `relationships` | Edges to other envelopes, with `status` (`suggested` / `confirmed` / `rejected`) and `discovered_by`. |
| `evidence` | Source evidence. |
| `validations` | Contradictions + model disagreements. |
| `security` | Signing + redaction metadata. |
| `exports` | Where this envelope was sent. |
| `extensions` | Open namespace (with 14 banned key names under `extensions.halobridge.*`). |
| `ai_usage` | Hashes + token counts + cost — never raw prompts. |
| `gallounits` | Text / image / audio units + their hashes + (optional) embeddings. |
| `certification` | Domain authority signature, if applicable. |
| `gstp` | Tamper-evident transport package. |
| `truth_ledger` | Append-only hash chain of claims + supersessions. |
| `trust` | Components, drivers, blockers, decision gates, policy outcomes (flat). |

Plus **23 optional sections** (see
[`docs/specs/gallodoc-core-v3-master-spec.md §3`](../specs/gallodoc-core-v3-master-spec.md)).

---

## Why v3 is different from a JSON schema

A JSON schema describes shape. GalloDoc v3 describes an **end-to-end
operational contract**:

- **Privacy invariants are enforced.** Raw prompts, raw responses, OAuth
  tokens, PHI/PII patterns, private keys, and 14 platform-internal block
  names are rejected by the validator and the release safety gate. The
  scan is baked into the release pipeline, not retrofitted at PR review.
- **Cross-envelope linking is first-class.** Linker-discovered
  relationships land with `status: "suggested"` and propagate to
  `confirmed`/`rejected` via human review — with the audit trail
  preserved.
- **Federation is first-class.** Cross-tenant matching policy is its own
  top-level block, not buried under `extensions`. Most-restrictive
  policy wins on intersection.
- **Embeddings are first-class.** They attach to GalloUnits, not to a
  separate vector index. Raw vectors never ship by default.
- **The query layer is safe-by-construction.** The NL → query planner
  emits `QueryPlan` objects with 6 safe filter primitives. No raw SQL
  is ever generated; the planner refuses to emit any string containing
  `SELECT`/`INSERT`/`UPDATE`/`DELETE`/semicolons/backticks.

---

## Five-minute install

```bash
pip install gallodoc
gallodoc connector convert --connector generic_json --input my_data.json --out env.gdoc.json
gallodoc validate env.gdoc.json
```

That produces a valid `gallodoc-core/v3` envelope and validates it. See
[`docs/specs/gallodoc-core-v3-master-spec.md §14`](../specs/gallodoc-core-v3-master-spec.md)
for the full 5-minute flow including embeddings, linking, and the NL → plan
command.

---

## What's open-source vs. paid

**Open-source (Apache 2.0):** schema, validator, projector, migrator,
connector SDK, linker, embeddings adapters, training lab, training
recipe for `gallodoc-bge-m3-v1`, federation policy + matching, NL → GQL
planner, GalloMarkdown layer, GSTP offline verifier, AI usage helpers,
GalloUnit segmenter, CLI. Everything you need to produce, validate,
link, and query envelopes yourself.

**Paid (HaloBridge):** the trained embedder weights, the cross-tenant
matching runtime, the AI/BI query execution backend, the HIM-C
certifier registry, the dashboard and review surfaces, regulated
compliance packs, the signing service for GSTP, and managed key
infrastructure.

---

## What GalloDoc is not

- **Not a database.** It's a file format. Drop the JSON into S3,
  Postgres, an object store, your audit log — whatever you already use.
- **Not an LLM.** It doesn't generate outputs. It wraps the outputs
  you already produce.
- **Not vendor lock-in.** The verifier is stdlib-only. The signing
  format is ed25519. You can leave at any time and your envelopes
  remain verifiable forever.
- **Not just for healthcare.** Invoices, contracts, support tickets,
  claims, marketing assertions, anything where "show your work" is
  the requirement.

---

## Next steps

- Read the [master spec](../specs/gallodoc-core-v3-master-spec.md).
- Read the [migration guide](../migration/v1-to-v3.md) if you have v1
  envelopes.
- Pick an audience-targeted guide:
  - Building a connector? → [`connector-guide.md`](connector-guide.md).
  - Running the linker in ops? → [`linker-guide.md`](linker-guide.md).
  - Training an embedder? → [`training-guide.md`](training-guide.md).
  - Compliance / governance lead? →
    [`privacy-and-governance-guide.md`](privacy-and-governance-guide.md).

---

*GalloDoc is the open-source layer of [HaloBridge](https://halobridge.ai).
HaloBridge sells the operational infrastructure on top — but the
standard and the offline tools are yours to keep.*
