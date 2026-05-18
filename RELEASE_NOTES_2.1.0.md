# GalloDoc Core 2.1.0 — Release Notes

**Theme:** *Give GalloDoc a document — get trusted Markdown plus a
validated GalloDoc envelope.*

GalloDoc Core 2.1 is an additive release. Every v1.x and v2.0 envelope
that validated under 2.0 still validates here. The on-the-wire
identifier (`gallodoc-core/v1`) is unchanged.

---

## What's new

### 1. GalloMarkdown (`*.gmd`) — bidirectional authoring layer

A human-readable Markdown dialect that compiles to a canonical GalloDoc
envelope and renders back from one. JSON remains the source of truth;
GalloMarkdown is for authoring, review, and audit packets.

**New modules**

- `gallodoc.markdown` — parser (`parse_gallomd`, `gallomd_to_gallodoc`,
  `validate_gallomd`).
- `gallodoc.markdown_renderer` — renderer (`gallodoc_to_gallomd`,
  `render_gallodoc_summary`, `render_gallodoc_section`).

**New CLI subcommands**

```bash
gallodoc md validate   report.gmd
gallodoc md compile    report.gmd --out report.gallodoc.json
gallodoc md inspect    report.gmd
gallodoc md render     report.gallodoc.json --out report.gmd
gallodoc md roundtrip  report.gmd
```

**Block grammar (v1)**

```
::gallodoc
doc_id: ...
document_type: ...
::

::artifact family=line_items id=art-001
description: ...
::

::evidence id=ev-001
source_ref: ...
hash: ...
summary: ...
::

::trust score=92 level=HIGH
grade: A
status: trusted
explanation: ...
::

::decision action=approve confidence=0.91 id=gate-001
reason: evidence_validated
::

::policy decision=allow id=pol-001
policy_name: contract_review_v1
policy_version: v1
::

::agent_security risk_level=high decision=block id=asc-001
risk_score: 87
summary: ...
::
```

Spec: [`docs/specs/gallomarkdown-v1.md`](docs/specs/gallomarkdown-v1.md).

### 2. Document conversion (`gallodoc convert`)

A new top-level CLI verb wraps the conversion pipeline. Pass any
supported document and receive a GalloMarkdown projection plus a
validated GalloDoc envelope.

```bash
gallodoc convert contract.pdf
gallodoc convert report.docx
gallodoc convert notes.txt
gallodoc convert export.json
```

Outputs (default):

```
contract.gmd
contract.gallodoc.json
```

**Options:** `--to gmd|json|both`, `--out-dir <dir>`,
`--redaction-mode auto|redacted|raw`, `--validate`, `--pretty`,
`--extract-artifacts`.

**Supported inputs (Phase 1, stdlib-only):**
`.txt`, `.md`, `.gmd`, `.json`, `.csv`, `.tsv`, `.html`, `.xml`, `.eml`.

**Supported inputs (Phase 2, optional packages):**
`.pdf` (`pip install gallodoc[pdf]`), `.docx` (`pip install gallodoc[docx]`),
`.xlsx` (`pip install openpyxl`).

When an optional package is missing the CLI prints a clear install hint
instead of crashing.

### 3. Examples

```
examples/markdown/
  basic.gmd
  contract_review.gmd
  chase_intelligence_packet.gmd
  agent_security_review.gmd
  rendered_from_gallodoc.gmd

examples/conversion/
  text_sample/sample.txt → sample.gmd + sample.gallodoc.json
  csv_sample/sample.csv  → sample.gmd + sample.gallodoc.json
  json_sample/sample.json → sample.gmd + sample.gallodoc.json
```

### 4. Tests

- `tests/test_gallomarkdown.py` — parser + safety contract.
- `tests/test_gallomarkdown_renderer.py` — renderer + redaction +
  roundtrip preservation.
- `tests/test_conversion.py` — txt / md / json / csv / gmd flows plus
  graceful pdf/docx fallback.

---

## Safety contract (unchanged direction, expanded scope)

The compile and render directions both reject / redact:

- raw prompts / responses (`raw_prompt`, `raw_response`,
  `prompt_text`, `response_text`)
- chain-of-thought / scratchpad
- private keys (PEM markers, OpenSSH blocks)
- bearer tokens, JWTs, OpenAI / AWS-shaped key markers
- secrets / credentials (`api_key`, `client_secret`, `bearer_token`, …)
- model weights, training payloads, retrieval chunks, PHI chunks
- SSN-shaped literals

Compile: hard error. Render: redacted to `[REDACTED]` plus a
`::warning type=safety_redaction` block.

---

## Compatibility

- Schema version constant unchanged (`gallodoc-core/v1`).
- Every `examples/v1_*` and `examples/v2_0` envelope still validates.
- The package now supports Python 3.10+; v2.1 adds **no required
  dependencies**.

---

## Migration

No migration required. To use the new authoring layer:

```bash
pip install --upgrade gallodoc
gallodoc convert your_document.pdf
gallodoc md roundtrip your_document.gmd
```

Optional dependencies for richer conversion:

```bash
pip install gallodoc[pdf]    # pypdf
pip install gallodoc[docx]   # python-docx
pip install openpyxl         # XLSX
```
