# GalloMarkdown / GalloMD v1

**Status:** Draft v1
**Authoring layer for GalloDoc Core.**
**Canonical source of truth: GalloDoc JSON.**

GalloMarkdown (`*.gmd`) is a human-readable Markdown dialect that compiles
into a valid GalloDoc envelope and that can be rendered back from one.

GalloMD does **not** replace GalloDoc JSON. It is an authoring / review
layer. JSON is canonical; round-trip tests must verify that the
compiled JSON validates against the frozen `gallodoc-core/v1` schema.

---

## 1. Design rules

1. **JSON is canonical.** A `.gmd` file is a *projection*. Compilation
   must always produce a structurally valid GalloDoc envelope.
2. **Markdown stays Markdown.** Anything outside a fenced GalloMD block
   is ordinary CommonMark. Headings, paragraphs, lists, and code fences
   are preserved as content/text and are never re-interpreted.
3. **Fenced GalloMD blocks are typed.** Each block opens with a `::name`
   line and closes with a single `::` line on its own.
4. **Safe by default.** Forbidden raw fields (raw prompts, raw responses,
   chain-of-thought, secrets, private keys, PHI literals) cause a hard
   parse error. The renderer redacts the same content with a warning
   block.
5. **Additive only.** New block types and attributes may be added in
   future minors but must not break existing `.gmd` files.

---

## 2. File shape

```
# GalloDoc: <title>

::gallodoc
schema_version: gallodoc-core/v1
doc_id: doc-001
document_type: contract
source: filesystem
::

## Content

Free-form Markdown text. Headings/paragraphs become GalloUnit candidates.

## Artifacts

::artifact family=line_items id=art-001
description: Service A
amount: 100
currency: USD
::

## Evidence

::evidence id=ev-001
source_ref: doc:contract-page-2
hash: sha256:abc...
summary: Quoted price line.
::

## Trust

::trust score=92 level=HIGH
grade: A
explanation: All evidence verified.
::

## Decisions

::decision action=approve confidence=0.91 id=dec-001
reason: evidence_validated
::

## Policy

::policy decision=allow id=pol-001
policy_version: contract_review_v1
::

## Agent Security

::agent_security risk_level=high decision=block id=asc-001
risk_score: 87
summary: Manifest declared a high-risk capability.
::
```

---

## 3. Block grammar

A block looks like:

```
::<block_name>[ key=value [key=value ...]]
key: value
multi
line
content
::
```

**Rules**

* `::<name>` must be at the start of a line (no leading whitespace).
* The closing `::` must be a line on its own (no leading whitespace, no trailing
  text).
* Inline attributes after the block name are space-separated `key=value`
  tokens. Values may be quoted with `"..."` for spaces.
* The body is parsed as a YAML-flavoured key/value map plus an optional
  free-text trailing summary. Unknown keys are preserved as block
  metadata.
* Blocks may not nest.
* A block opening before the previous block has closed is a parse error.

Reserved block names (v1):

| Block            | Maps to envelope section                                       |
|------------------|----------------------------------------------------------------|
| `gallodoc`       | Header — `schema_version`, `identity`, `source`, `purpose`     |
| `artifact`       | `extensions.gallomd_artifacts[]`                               |
| `evidence`       | `evidence.refs[]`                                              |
| `trust`          | `trust_decision.trust_scores[]`                                |
| `decision`       | `trust_decision.decision_gates[]`                              |
| `policy`         | `trust_decision.policy_outcomes[]` (or `policy_governance`)    |
| `agent_security` | `agent_supply_chain_security.findings[]` (summary form)        |
| `warning`        | Renderer-only — included when content was redacted             |

Future blocks (additive): `consent`, `custody`, `attestation`,
`workflow`, `query`, `vector`, `human_review`.

---

## 4. The `::gallodoc` header

The first GalloMD block in a file SHOULD be `::gallodoc`. It populates
the envelope header.

| Key                  | Required | Default                   | Maps to                              |
|----------------------|----------|---------------------------|--------------------------------------|
| `schema_version`     | no       | `gallodoc-core/v1`        | `schema_version`                     |
| `doc_id`             | yes      | —                         | `identity.gallodoc_id` + `document_id` |
| `title`              | no       | first H1 in the file      | `identity.title`                     |
| `document_type`      | yes      | —                         | `identity.document_type`             |
| `mime_type`          | no       | `text/markdown`           | `identity.mime_type`                 |
| `source`             | no       | `gallomarkdown`           | `source.source_system`               |
| `source_kind`        | no       | `markdown_authored`       | `source.source_kind`                 |
| `connector_slug`     | no       | `gallomarkdown`           | `source.connector_slug`              |
| `created_at`         | no       | now (ISO-8601)            | `identity.created_at`                |
| `primary_intent`     | no       | `authoring`               | `purpose.primary_intent`             |
| `workflow_intent`    | no       | `gallomarkdown_authoring` | `purpose.workflow_intent`            |
| `requested_by`       | no       | `""`                      | `purpose.requested_by`               |
| `confidence`         | no       | `1.0`                     | `purpose.confidence`                 |

---

## 5. Content / GalloUnit candidates

Markdown text outside any fenced GalloMD block becomes the document
content. The compiler performs the following:

1. The full normalized Markdown body is hashed and stored at
   `extensions.gallomd_source.markdown_hash`.
2. Each H1/H2/H3 heading + its following paragraph is recorded as a
   GalloUnit candidate (`gallounits.units[]`) with
   `unit_type="heading_block"` and `semantic_role="content"`.
3. Plain paragraphs become `unit_type="paragraph"` units.

The compiler never invents trust scores, signatures, or hashes that
were not declared by the author. Hashes are computed only over content
already present.

---

## 6. Compiled envelope guarantees

After `gallomd_to_gallodoc(text)`, the returned envelope:

* has every required top-level key from the frozen schema
  (`identity`, `source`, `purpose`, `lifecycle`, `activity`,
  `relationships`, `evidence`, `validations`, `security`, `exports`,
  `extensions`, `ai_usage`, `gallounits`, `certification`, `gstp`,
  `truth_ledger`),
* sets safe empty defaults for sections the author did not write,
* declares `schema_version = "gallodoc-core/v1"`,
* validates with the stdlib validator (`validate_envelope`).

The envelope MUST round-trip:
`gallomd_to_gallodoc → gallodoc_to_gallomd → gallomd_to_gallodoc`
must produce the same canonical core fields (doc id, document type,
declared trust scores, declared decisions, declared findings).

---

## 7. Safety rules (compile and render)

A `.gmd` file is rejected at compile time if it contains any of:

* a key named (case-insensitive) `raw_prompt`, `raw_response`,
  `prompt_text`, `response_text`, `chain_of_thought`, `cot_trace`,
  `hidden_reasoning`, `scratchpad`, `private_key`, `bearer_token`,
  `access_token`, `refresh_token`, `client_secret`, `api_key`,
  `secret_value`, `credential_value`, `raw_secret`, `model_weights`,
  `lora_weights`, `retrieval_chunk_body`, `phi_chunk`, `raw_phi`,
  `raw_sql`, `password`,
* a string that matches a JWT shape (`eyJ...`),
* a literal SSN (`NNN-NN-NNNN`),
* a `-----BEGIN ... PRIVATE KEY-----` PEM marker,
* a `sk-<alphanum>` style API key marker.

The renderer applies the same set: it replaces the value with
`[REDACTED]` and emits a `::warning type=safety_redaction` block at
the top of the file.

---

## 8. CLI

```
gallodoc md validate FILE.gmd
gallodoc md compile FILE.gmd --out FILE.gallodoc.json
gallodoc md inspect FILE.gmd
gallodoc md render  FILE.gallodoc.json --out FILE.gmd
gallodoc md roundtrip FILE.gmd
```

Exit codes: `0` on success, `1` on validation/safety failure.

---

## 9. Versioning

The block grammar is versioned independently of the envelope. The
current grammar is `gallomarkdown/v1`. New blocks may be added in
`v1.x`; structural breaks require `v2`. The compiler always emits
`gallodoc-core/v1` envelopes — the canonical schema is unchanged.
