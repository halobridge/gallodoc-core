---
title: "GalloDoc 1.2 — Consent, Custody, and Attestation"
version: "1.2"
status: release-candidate
audience: "compliance teams; privacy teams; audit teams; legal operations; AI governance teams"
last_updated: "2026-05-02"
keywords: "consent ledger, chain of custody, attestation, redaction, evidence quality, GalloDoc 1.2"
---

# Consent, Custody, and Attestation

## Executive Summary

Execution control is necessary, but it is not enough. Enterprises also need to
prove why a document or data element was allowed to be used, who approved or
reviewed it, where it traveled, what was redacted, and whether the evidence was
good enough to support the resulting decision.

These are not theoretical governance questions. They appear in audits,
customer security reviews, litigation support, healthcare workflows, financial
operations, insurance claims, procurement reviews, and AI oversight programs.

GalloDoc 1.2 adds a compliance-oriented layer for Consent, Custody, and
Attestation. It introduces:

- Consent Ledger.
- Chain of Custody.
- Human Decision Records, including HIM-C.
- Attestation Blocks.
- Redaction Manifest.
- Evidence Quality.

Together, these blocks allow every governed document to answer:

- Who touched it?
- Why did they touch it?
- What did they do?
- Where did it go?
- Was it redacted?
- Was the evidence valid enough to rely on?

GalloDoc 1.2 turns document accountability from scattered workflow metadata
into portable, privacy-safe proof.

## The Accountability Problem

Enterprise workflows rarely fail because nobody has a document. They fail
because nobody can prove the accountable history of the document.

A file may have passed through multiple systems, reviewers, exports, AI
pipelines, redaction steps, and decision queues. Each system may keep logs, but
the logs are usually fragmented. One application records upload history.
Another records review status. Another stores exports. Another stores consent.
Another stores redactions. Another stores AI calls.

When an auditor, customer, regulator, or internal reviewer asks a direct
question, the enterprise has to assemble an answer manually:

- Who approved this use?
- Was consent active?
- Which role reviewed the document?
- Which version was exported?
- Where did the artifact travel?
- Was sensitive content redacted before sharing?
- What evidence supported the final attestation?

This is an accountability gap. It is also an AI safety gap. AI systems can
accelerate document processing, but they cannot safely replace proof of consent,
custody, and human accountability.

## Why Consent Needs a Ledger

Consent is often treated as a status flag: yes or no, active or inactive,
approved or denied. That is too weak for enterprise governance.

Real consent has context. It has a basis, a scope, an actor role, an effective
period, a reference to an artifact or policy, and a relationship to a specific
workflow. Consent can expire. It can be limited to one purpose. It can require
redaction. It can authorize internal processing but not external transmission.

GalloDoc 1.2 introduces a Consent Ledger so consent can be represented as a
series of metadata entries rather than a single ambiguous flag. The ledger
stores roles and artifact references, not raw signatures or personal
identifiers. It gives downstream systems a portable way to inspect whether a
document's use was authorized for the declared purpose.

This is especially important when document intelligence is reused. A document
may be valid for one workflow but not another. Without a consent ledger,
systems either over-restrict reuse or over-trust access.

## Chain of Custody for Digital Documents

Physical custody has long been understood in legal and compliance contexts. The
same principle now applies to digital document intelligence.

If a document-derived record drives a business decision, the enterprise needs
to know where it came from, where it went, which role handled it, which export
was generated, and which hash or reference identifies the transferred artifact.

GalloDoc 1.2 adds Chain of Custody events to the envelope. These events use
opaque locations and hashes rather than raw URLs or secrets. The goal is not to
expose every internal system detail. The goal is to preserve a trustworthy
custody history that can be inspected without leaking sensitive infrastructure
or content.

Custody becomes part of the document's portable record, not a set of isolated
application logs.

## Human Decision Records and HIM-C

AI governance often focuses on model outputs, but enterprise accountability
still depends on human decision records. A human reviewer may approve, deny,
correct, escalate, certify, or override a document-derived result. Those
decisions need to be captured in a way that is precise enough for audit but
safe enough for exchange.

GalloDoc 1.2 includes Human Decision Records, including HIM-C: human-in-the-
middle control. HIM-C records the presence of accountable human judgment. It
does not require exposing unnecessary personal data. It can record reviewer
role, decision type, timestamp, referenced evidence, and decision summary.

This matters because "human review" is often claimed but not proven. GalloDoc
1.2 makes human oversight inspectable. A reviewer can see not only that a human
was involved, but which role acted, which decision was made, and which evidence
or policy context supported the action.

## Attestation Blocks

Attestation is stronger than status. A status says what the system believes
right now. An attestation says an authorized party has certified a trust state
under a declared basis.

GalloDoc 1.2 adds Attestation Blocks so document trust can be recorded as
portable records. These may summarize review posture, certification basis,
evidence references, policy alignment, or trust state.

Attestation is powerful because it allows downstream systems to rely on prior
review without blindly re-performing it. A consuming system can inspect the
attestation, check the evidence quality, assess the certifying role, and decide
whether to accept the document for its workflow.

## Redaction Manifest

Redaction is often treated as a visual operation: black boxes on a page or
fields suppressed in an export. But for governed document exchange, redaction
must be an auditable operation.

GalloDoc 1.2 includes a Redaction Manifest. It records what categories or
regions were redacted, why, by which policy or role, and in relation to which
export or document version. It does not need to disclose the sensitive content
that was removed.

This allows enterprises to prove that a shared artifact was privacy-scoped.
Downstream reviewers can understand not just that redaction occurred, but which
policy basis and workflow context controlled it.

## Evidence Quality

Not all evidence is equal. An OCR extraction from a low-quality scan, a
conflicting field from two sources, a partial record, or a stale export should
not carry the same trust as a clean, verified, source-authenticated document.

GalloDoc 1.2 adds Evidence Quality metadata so consumers can evaluate the
strength of the supporting material. Evidence quality can summarize confidence,
completeness, contradiction state, validation posture, and review status.

This is a practical governance control. It helps prevent weak evidence from
silently becoming strong operational truth.

## Privacy-Safe Accountability

GalloDoc 1.2 is designed for accountability without oversharing. It avoids raw
signatures, raw personal identifiers, raw URLs, secrets, and sensitive payloads.
It favors roles, hashes, opaque references, timestamps, policy identifiers, and
safe summaries.

That design is important for enterprise adoption. Accountability records need
to be durable and portable, but they should not create a new privacy risk.

## Business Impact

GalloDoc 1.2 gives enterprises a stronger answer to compliance and trust
questions. Compliance teams gain portable consent and custody records.
Security teams gain evidence that sensitive artifacts were handled under
policy. Legal teams gain a clearer chain of document events. Operations teams
gain reusable proof of review and attestation. AI governance teams gain a way
to prove human accountability around automated workflows.

The result is a document layer that can stand up to scrutiny. It does not just
say "this document was processed." It says why processing was allowed, who
reviewed it, where it went, what was redacted, and whether the evidence was
good enough.

## Conclusion

Enterprises cannot govern documents or AI with execution records alone. They
need consent, custody, human accountability, attestation, redaction, and
evidence quality.

GalloDoc 1.2 provides those controls as additive, privacy-safe metadata on top
of the GalloDoc Core envelope. It turns document accountability into something
portable and inspectable.

The enterprise question becomes: "Can this document prove its own permission,
custody, review, redaction, and trust state?"

With GalloDoc 1.2, the answer can be yes.
