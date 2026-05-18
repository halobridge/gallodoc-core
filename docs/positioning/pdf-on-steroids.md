# GalloDoc and PDFs

**Audience:** practitioners who already use PDFs (or other portable
document formats) and want to understand how GalloDoc relates to them.
**Reading time:** ~4 minutes.

---

## The short answer

GalloDoc is not a PDF competitor. It lives at a **different layer**.

| Layer | What it does | Example |
|---|---|---|
| **Rendering** | Show humans something to read. | PDF, DOCX, HTML, Markdown. |
| **Operational** | Capture what a system did with a document — inputs, models, prompts, outputs, evidence, decisions, trust, relationships. | **GalloDoc v3.** |

A PDF is a *render*. A GalloDoc envelope is a *record of the operation
that produced or consumed the render*. The two compose: a contract review
workflow has a PDF (the contract) and a GalloDoc envelope (the operation:
"reviewed by claim-extractor v2.3, hashed, gated by trust component
'completeness' at 0.92, confirmed by reviewer u-001 on 2026-05-15").

---

## What GalloDoc adds on top of a PDF

If you have only the PDF:

- You know what the document looks like.
- You don't know which model classified it.
- You don't know which evidence was used.
- You don't know which reviewer signed off.
- You don't know which trust components passed.
- You don't know which other envelopes it's linked to.
- You can't replay the decision deterministically.

If you have the PDF **plus** a GalloDoc envelope:

- The PDF's content hash lives in `identity.content_hash`. Any change
  to the PDF invalidates the envelope.
- The operation that produced or reviewed it lives in
  `lifecycle.stages[]`.
- The model versions, token counts, and costs live in `ai_usage`. Raw
  prompts and responses are stored as hashes, never as text.
- The reviewer's decision (and the policy gate that approved it) live
  in `trust.decision_gates[]`.
- Cross-document relationships live in `relationships.relationships[]`
  with explicit `status` and `discovered_by`.
- The tamper-evident GSTP package wraps it all in a hash chain that
  verifies offline with a public key.

---

## Why not put this in the PDF?

You can — and producers often do (XMP metadata, embedded JSON, the
`/Catalog/Metadata` stream). The problem is:

1. **PDF metadata is loosely structured.** Each producer ships its own
   shape. You can't write a portable validator. GalloDoc envelopes are
   `gallodoc-core/v3` and validate identically anywhere.
2. **PDF metadata is not portable across formats.** What about audio?
   Video? CSV rows? SQL claim records? GalloDoc envelopes wrap any
   operation regardless of the source modality. The `gallounits` block
   carries text / image / audio units uniformly.
3. **PDF metadata is not queryable.** You can't easily ask "every
   envelope produced in May with confidence below 0.7 against
   `gpt-4o-2024-08-06`." With GalloDoc + the v3 AI/BI planner, that's
   a single NL → QueryPlan call.

GalloDoc doesn't replace the PDF. It records the operation **about**
the PDF (or any source document) in a portable, queryable, verifiable
shape.

---

## How they compose in practice

1. A producer ingests a PDF using the `gallodoc connector convert`
   command (with a PDF-aware connector like `pdf_file_metadata`).
2. The connector emits a `gallodoc-core/v3` envelope. The PDF stays
   on disk; the envelope carries `identity.content_hash` pointing at
   it.
3. Downstream operations (classification, extraction, review)
   append to the envelope's `lifecycle.stages[]` and `trust.*` arrays.
4. The GSTP package
   ([`docs/gstp-v1.md`](../gstp-v1.md)) signs the envelope's canonical
   JSON. The PDF itself is not signed by GSTP; its hash is.
5. The auditor opens the envelope, verifies the GSTP signature, and
   re-hashes the PDF to confirm it matches `identity.content_hash`.

---

## What about XFA, signed PDFs, PAdES, etc.?

Those are PDF-internal signing mechanisms. They're complementary to
GalloDoc:

- **PAdES / signed PDFs** verify the PDF was signed by a specific
  entity. GalloDoc verifies the *operation* the PDF participated in —
  who reviewed it, with what model, at what trust threshold.
- A claim envelope can carry the signed PDF's hash *and* the GSTP
  signature of the envelope itself. Two layers of provenance.

---

## When you'd use just a PDF

- The document never participates in an automated operation.
- You don't need to replay a decision later.
- Compliance doesn't ask "show your work."

When any of those flip, GalloDoc starts paying for itself.

---

## When you'd use a GalloDoc envelope

- Your AI pipeline produces operations that compliance needs to
  reconstruct.
- You're moving operations between systems and want one canonical
  record.
- You want to query operations after the fact ("every invoice approved
  in May where the linker suggested an employee approver match").
- You want offline-verifiable provenance.

---

## Further reading

- [`what-is-gallodoc.md`](what-is-gallodoc.md) — 90-second positioning.
- [`connector-guide.md`](connector-guide.md) — how to wrap a PDF (or
  any source) into an envelope.
- [`docs/specs/gallodoc-core-v3-master-spec.md`](../specs/gallodoc-core-v3-master-spec.md)
  — the full spec.
