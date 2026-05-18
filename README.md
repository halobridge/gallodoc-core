# GalloDoc

**Portable AI-ready documents with built-in trust, evidence, governance, and auditability.**

---

## 🚀 5-minute install + first envelope + first query

```bash
pip install gallodoc
gallodoc connector convert --connector generic_json --input my.json --out env.gdoc.json
gallodoc validate env.gdoc.json
gallodoc aibi plan "show invoices linked to John" --envelope env.gdoc.json
```

In minutes you can:

* convert raw data into governed envelopes
* validate AI-safe document structure
* attach evidence + trust metadata
* generate safe natural-language query plans

For details see the audience-targeted positioning docs:

| Doc | Audience |
|---|---|
| [`docs/positioning/what-is-gallodoc.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/positioning/what-is-gallodoc.md) | New users — 90-second pitch |
| [`docs/positioning/pdf-on-steroids.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/positioning/pdf-on-steroids.md) | Practitioners coming from PDF workflows |
| [`docs/positioning/connector-guide.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/positioning/connector-guide.md) | Connector developers |
| [`docs/positioning/semantic-encoder-guide.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/positioning/semantic-encoder-guide.md) | Embedding-pipeline developers |
| [`docs/positioning/linker-guide.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/positioning/linker-guide.md) | Ops engineers running the linker |
| [`docs/positioning/training-guide.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/positioning/training-guide.md) | ML engineers reproducing `gallodoc-bge-m3-v1` |
| [`docs/positioning/privacy-and-governance-guide.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/positioning/privacy-and-governance-guide.md) | Compliance / governance leads |

For the full spec: [`docs/specs/gallodoc-core-v3-master-spec.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/specs/gallodoc-core-v3-master-spec.md).
For migration from v1: [`docs/migration/v1-to-v3.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/migration/v1-to-v3.md).

---

## What is GalloDoc?

**GalloDoc is an open standard for portable operational intelligence documents.**

A GalloDoc envelope is one JSON file that captures everything a
downstream auditor, reviewer, or AI/BI query engine needs to verify,
reproduce, or extend the operation that produced it. Inputs (by hash).
Models (by version). Prompts (by hash — never the raw text). Outputs.
Evidence. Reviewer decisions. Trust scores. Relationships to other
envelopes.

GalloDoc is:

> A simple JSON format that grows with you —
> from basic document storage → to full AI trust and governance.

---

# 🪜 5 Levels of GalloDoc

You don’t need everything.

Each level works on its own.

---

## 🟢 Level 1 — Just use it like JSON

```json
{
  "document": {
    "doc_id": "123",
    "type": "contract"
  },
  "content": {
    "text": "This agreement is between..."
  }
}
```

✔ Validate documents
✔ Store structured data
✔ Build simple APIs

---

## 🟡 Level 2 — Structured Data

```json
{
  "artifacts": [
    {
      "family": "line_items",
      "data": [
        { "item": "Service A", "price": 100 }
      ]
    }
  ]
}
```

✔ Extract fields
✔ Normalize messy documents
✔ Compare across systems

---

## 🔵 Level 3 — AI + Evidence

```json
{
  "ai_outputs": [{ "type": "classification", "result": "high_risk" }],
  "evidence": [{ "type": "document", "reference": "clause_12" }]
}
```

✔ AI results with proof
✔ Explainable outputs
✔ RAG-ready structure

---

## 🔴 Level 4 — Trust + Decisions

```json
{
  "trust": { "score": 92 },
  "decisions": [{ "action": "approve" }]
}
```

✔ Trust scoring
✔ Decision tracking
✔ Audit-ready workflows

---

## 🟣 Level 5 — Security + Agent Safety

```json
{
  "agent_supply_chain_security": {
    "risk_level": "high",
    "decision": "block"
  }
}
```

✔ Scan AI tools / agents
✔ Detect malicious behavior
✔ Secure automation

---

## ✍️ Write GalloDocs in Markdown — GalloMarkdown

GalloMarkdown (`.gmd`) is a human-readable layer for GalloDoc.
JSON GalloDoc remains canonical. GalloMarkdown is for **authoring**,
**review**, and **audit packets**.

```markdown
# GalloDoc: Contract Review

::gallodoc
doc_id: doc-contract-001
document_type: contract
::

## Content

A 12-month managed-services agreement with…

## Trust

::trust score=92 level=HIGH
grade: A
status: trusted
explanation: All evidence verified.
::

## Decisions

::decision action=approve confidence=0.91 id=gate-001
reason: evidence_validated
::
```

```bash
gallodoc md compile examples/markdown/contract_review.gmd
```

GalloMarkdown is **bidirectional**:

```bash
# Render an existing GalloDoc envelope as readable Markdown.
gallodoc md render examples/v1_6/gallodoc_agent_supply_chain_security.json --out review.gmd

# Edit it.
$EDITOR review.gmd

# Compile it back to canonical JSON.
gallodoc md compile review.gmd --out review.gallodoc.json
```

Roundtrip safety: the renderer redacts unsafe content (raw prompts,
secrets, PHI patterns, private keys) and writes a
`::warning type=safety_redaction` block. The compiler rejects the same
patterns at parse time. JSON is the source of truth.

Spec: [`docs/specs/gallomarkdown-v1.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/specs/gallomarkdown-v1.md).

---

## 📥 Convert documents into GalloDoc

Start with documents, not JSON.

```bash
gallodoc convert contract.pdf
gallodoc convert report.docx
gallodoc convert notes.txt
gallodoc convert export.json
```

Generates:

```
contract.gmd            # human-readable projection
contract.gallodoc.json  # canonical envelope
```

**Phase 1 formats (stdlib-only):** `.txt`, `.md`, `.gmd`, `.json`,
`.csv`, `.html`, `.xml`, `.eml`.

**Phase 2 formats (optional packages):** `.pdf` (`pip install gallodoc[pdf]`),
`.docx` (`pip install gallodoc[docx]`), `.xlsx` (`pip install openpyxl`).

Useful flags:

```bash
gallodoc convert contract.pdf \
  --to both \
  --out-dir ./out \
  --redaction-mode auto \
  --extract-artifacts \
  --validate \
  --pretty
```

---

# 🔥 What actually happens

INPUT
PDF / API / Email / FHIR / JSON

↓

GalloDoc

* structured data
* extracted evidence
* relationships
* lifecycle

↓

OUTPUT

✔ Trust score
✔ Audit packet
✔ Policy validation
✔ Export-ready data

---

# 💥 Why this exists

Most systems:

* store data
* move data
* expose data

They do NOT prove it.

GalloDoc does.

---

# ⚡ What you get out of the box

* GalloUnits → stable semantic evidence layer
* AI usage ledger → full traceability (hashes only)
* Artifact extraction → structured signals
* GSTP → tamper-evident packaging

All:

* local
* offline
* zero required dependencies

---

# 🧩 What can you build?

* Document AI pipelines
* RAG systems with proof
* Audit/compliance systems
* AI decision engines
* Secure agent platforms

---

# 🛡️ Safety first

GalloDoc is designed to be safe by default:

* ❌ No raw prompts/responses
* ❌ No secrets
* ❌ No PHI leakage

Only:

* hashes
* summaries
* structured data

---

# 📦 Quick examples

```bash
examples/
  basic.json
  structured.json
  ai.json
  trust.json
  security.json
```

---

# 🧠 The big idea

GalloDoc turns documents into:

> **Verifiable, trusted AI-ready data**

---

# 📌 Project status

**GalloDoc Core 3.0.0** — Python package **3.0.0**, Development Status :: 4 - Beta
Schema family: `gallodoc-core/v3` (with parallel `gallodoc-core/v1` validator for 6 months from 2026-05-17)

| Version    | Focus                |
| ---------- | -------------------- |
| v1.0       | Document envelope    |
| v1.1       | Governance           |
| v1.2       | Consent + custody    |
| v1.3       | Risk + residency     |
| v1.4       | Observability        |
| v1.5       | Trust + decisions    |
| v1.6       | Agent supply chain   |
| 2.0        | Query · Vector · Relationships · Versioning · Policy · Access · Human Review · Workflow · Connector Lineage · Compute Trace · Artifact BOM |
| 2.1        | GalloMarkdown (`.gmd`) authoring/review layer + document conversion |
| **3.0**    | **Envelope rev to `gallodoc-core/v3` — consolidated `trust` + `relationships` + `source` + `lifecycle`; new `federation` block; open-source connector SDK, linker, embeddings adapter, training lab, trained-embedder recipe, NL→GQL planner** |

- 3.0 master spec: [`docs/specs/gallodoc-core-v3-master-spec.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/specs/gallodoc-core-v3-master-spec.md)
- 3.0 release notes: [`RELEASE_NOTES_3.0.0.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/RELEASE_NOTES_3.0.0.md)
- v1 → v3 migration guide: [`docs/migration/v1-to-v3.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/migration/v1-to-v3.md)
- 2.1 release notes: [`RELEASE_NOTES_2.1.0.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/RELEASE_NOTES_2.1.0.md)
- 2.0 release notes: [`RELEASE_NOTES_2.0.0.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/RELEASE_NOTES_2.0.0.md)

---

# 🧪 CLI examples

```bash
gallodoc validate examples/gallodoc_pdf_contract.json
gallodoc inspect examples/gallodoc_pdf_contract.json --json
gallodoc units sample.txt --json
gallodoc extract sample.txt --json
gallodoc gstp verify path/to/package.gstp/

# GalloMarkdown — bidirectional authoring/review layer (v2.1)
gallodoc md compile   examples/markdown/contract_review.gmd
gallodoc md render    examples/v1_6/gallodoc_agent_supply_chain_security.json
gallodoc md roundtrip examples/markdown/contract_review.gmd

# Document conversion (v2.1)
gallodoc convert examples/conversion/text_sample/sample.txt --validate
```

---

# 🧬 Advanced (optional)

GalloDoc also supports:

* full provenance tracking
* AI usage ledger (hash-based)
* GalloUnits (model-agnostic evidence units)
* GSTP verification

See:

* [`docs/gallodoc-core-v1.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/gallodoc-core-v1.md)
* [`docs/gallodoc-units-v1.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/gallodoc-units-v1.md)
* [`docs/ai-usage-ledger.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/docs/ai-usage-ledger.md)

---

# 🚀 Platform in Action

(Your existing GIF + image block stays here)

---

# 🧭 Philosophy

> Start simple.
> Add trust when you need it.

---

# 📄 License

Apache 2.0

---

# 🔐 Security

See [`SECURITY.md`](https://github.com/gsavitch/gallomvp/blob/v3.0.0/opensource/gallodoc-core/SECURITY.md).
Never submit real PHI or secrets.

---

# 🚀 GalloDoc

Simple to start.
Powerful when you need it.
