# GalloDoc Core v3 — Embedder Training Lab

**Status:** Active. Open-source. Ships only the data pipeline — never weights.

The training lab turns human-curated v3 envelopes into a training set the
GalloDoc-trained embedder (prompt 07) can consume. It is implemented under
`gallodoc.training` and exposes a single CLI subcommand,
`gallodoc training export-pairs`.

This spec is locked against the five anchor decisions in
[`docs/v3-design/07_decisions.md`](../../../../docs/v3-design/07_decisions.md).
The most load-bearing decision for this prompt is **Decision 3**: the
linker writes into `relationships` with `status: "suggested"`, promoted to
`confirmed` / `rejected` via `relationship_decisions[]`. Linker-discovered
pairs that a human confirmed are the **highest-quality positive training
pairs** — machine-proposed plus human-confirmed — and the exporter does
**not** filter them out.

---

## 1. Overview

The training lab's job is to read a v3 envelope (or a list of them) and
emit a stream of training pairs in JSONL. Each pair is a single
`(source, target, label)` example that downstream embedder training code
(prompt 07) can ingest without ever touching the original envelope.

The exporter is **open-source by construction** — pairs are scrubbed
through `gallodoc.projection.safety.assert_no_enterprise_leakage` before
they are emitted, and the export aborts on any leak (no skip path, no
`--unsafe` flag).

The exporter is also **deterministic**: same input envelopes plus same
seed always produces the same set of pairs, in the same order, with the
same train/dev/test partition. This is a hard requirement so the prompt
07 trainer's "this model was trained on this data" claim is reproducible.

---

## 2. Training pair schema

Each emitted pair is a JSON object with exactly the following 11 keys:

```json
{
  "pair_id": "pair_<sha256[:16]>",
  "source_gallodoc_ref": "...",
  "target_gallodoc_ref": "...",
  "relationship_type": "<v2.0 enum>",
  "semantic_intent": null | "<vocabulary value>",
  "label": "match" | "non_match" | "uncertain",
  "evidence_refs": ["..."],
  "reviewer_decision": {
    "decision_id": "...",
    "verdict": "confirmed" | "rejected",
    "decided_by": "...",
    "decided_at": "..."
  } | null,
  "confidence": 0.0,
  "discovered_by": "...",
  "created_at": "..."
}
```

Field notes:

- `pair_id` is deterministic: `"pair_" + sha256(f"{source_ref}::{target_ref}::{rel_type}::{label}")[:16]`. Re-running the exporter on the same inputs produces identical IDs.
- `source_gallodoc_ref` / `target_gallodoc_ref` are the
  `source_document_ref` / `target_document_ref` strings from
  `relationships.relationships[]` — no document content is included.
- `relationship_type` is the v2.0 enum value carried through from the
  source relationship entry.
- `semantic_intent` (Decision 5) is the `::semantic_intent` vocabulary
  value if the relationship has one. `null` otherwise.
- `label` is closed: `match` (confirmed positive),
  `non_match` (rejected positive or synthetic hard negative),
  `uncertain` (suggested-only — for downstream curation, never used
  directly as supervision).
- `evidence_refs` is the list of `evidence_id` values that
  `relationship_evidence[]` carries for this relationship.
- `reviewer_decision` is `null` for uncertain and for synthetic
  hard-negative pairs. For confirmed/rejected pairs it carries the
  matching `relationship_decisions[]` record verbatim.
- `confidence` is the confidence on the source relationship entry,
  or `0.0` for synthetic hard negatives.
- `discovered_by` is carried through verbatim from the source
  relationship entry. For synthetic negatives the exporter sets
  `"hard_negative:<strategy>"`.
- `created_at` is the ISO 8601 timestamp at which the pair was emitted.

The `label` enum is closed at three values: `match`, `non_match`,
`uncertain`. Anything else is a bug.

---

## 3. Pair sources & filters

The exporter recognizes four sources of pairs in a v3 envelope:

### 3.1 Positives — `label: "match"`

`relationships.relationships[]` entries with `status == "confirmed"`
**AND** a matching `relationship_decisions[]` record. The decision
record is mandatory for confirmed positives — without it the pair has
no audit trail and is skipped (inconsistent state).

**Includes linker-discovered + human-confirmed entries** (Decision 3).
That is, entries where `discovered_by` matches `/linker/i` AND
`status == "confirmed"` AND there is a matching decision record are the
highest-quality supervision signal. The exporter does **not** filter
them out. The `discovered_by` field is carried through so downstream
analysis can re-weight by origin.

### 3.2 Negatives — `label: "non_match"`

`relationships.relationships[]` entries with `status == "rejected"`
AND a matching `relationship_decisions[]` record. The decision record
is mandatory for rejected pairs — without it the pair has no audit
trail and is skipped (inconsistent state).

### 3.3 Uncertain — `label: "uncertain"`

`relationships.relationships[]` entries with `status == "suggested"`
and no matching decision record. These are emitted as
`label: "uncertain"` and carried through to the JSONL output for
downstream curation. They are **not** valid supervision signal — the
prompt 07 trainer should filter them out before computing a loss.

### 3.4 Hard negatives — `label: "non_match"`

Synthetic negatives generated per the four deterministic strategies in
§5. Each strategy produces pairs with
`discovered_by: "hard_negative:<strategy>"`. Hard negatives are
optional — the CLI gates them behind `--include-hard-negatives`.

### 3.5 Skip rules

The following relationship entries are **skipped** (not emitted):

- `status == "confirmed"` with no matching `relationship_decisions[]`
  record (inconsistent state — should be caught by the validator).
- `status == "rejected"` with no matching `relationship_decisions[]`
  record (same).
- `status == "suggested"` with a matching `relationship_decisions[]`
  record (the decision should have flipped the status — inconsistent
  state).
- Any `status` value outside `{"suggested", "confirmed", "rejected"}`
  (Decision 3 closes the enum — invalid value).

---

## 4. Hard-negative generator — four deterministic strategies

The generator emits synthetic `label: "non_match"` pairs sampled from
the cross-product of envelopes. Each strategy is deterministic — same
input envelopes produce the same set of hard negatives in the same
order. Each strategy caps its output at 10 pairs per group to keep the
pipeline bounded.

### 4.1 `same_org_wrong_person`

Group envelopes by `source.source_system`. Within each group, find
pairs of envelopes where `identity.document_type` contains `person`
or `employee` AND the two envelopes have different `gallodoc_id`s.
The expected use: prevents the embedder from over-relying on
organization fingerprints when matching person-level identity.

### 4.2 `same_vendor_wrong_invoice`

Group envelopes by vendor metadata (via a `truth_ledger.claims[]`
entry with `field_path == "vendor_name"`, or via `gallounits.units[]`
content if no truth ledger entry exists). Within each vendor group,
pair envelopes where `identity.document_type` is `invoice` and the
two envelopes have different `gallodoc_id`s. Prevents the embedder
from over-fitting on vendor identity for invoice matching.

### 4.3 `similar_clause_different_obligation`

Pair envelopes that share at least one
`gallounits.units[].semantic_role` value AND whose
`truth_ledger.claims[].field_path` sets are disjoint. Prevents the
embedder from collapsing different obligations onto the same vector
when they happen to share a role.

### 4.4 `same_customer_name_different_domain`

Pair envelopes that share a customer-name-shaped string in
`gallounits.units[].content_summary` (substring match on a configurable
set of customer-name tokens) AND whose `source.source_system` differs.
Real-world ambiguity case — same name, different identity.

Each strategy emits pairs with:

- `relationship_type = "related_to"` (the relationship is synthetic —
  the actual edge does not exist in the envelope).
- `label = "non_match"`.
- `reviewer_decision = None`.
- `confidence = 0.0`.
- `discovered_by = f"hard_negative:{strategy}"`.
- `evidence_refs = []`.
- `semantic_intent = None`.

---

## 5. Deterministic splitter

`split_train_dev_test(pairs, *, seed=42, ratios=(0.8, 0.1, 0.1))`
partitions pairs into three lists.

Implementation: hash `f"{pair_id}::{seed}"` with sha256, take the
result modulo 1000, and assign to a bucket. Buckets `[0, 800)` → train,
`[800, 900)` → dev, `[900, 1000)` → test. This guarantees the **same
pair always lands in the same split** across runs and across input
orderings.

Ratios must sum to 1.0 (±1e-6). Negative ratios raise. Empty inputs
produce three empty lists.

---

## 6. Privacy safety scan

Every pair passes through `assert_no_enterprise_leakage` (Codex 02)
before the export returns. The wrapper
`assert_pairs_clean(pairs)` walks the pair list and re-raises the
first `EnterpriseLeakageError`, identifying the pair index that
tripped the scan.

There is no skip path. There is no `--unsafe` flag. If the source
envelopes contain a leak pattern (SSN-like, MRN-like, private key
shape, platform-internal key, banned `extensions.halobridge.*` key)
the export aborts and the user must clean the source data.

---

## 7. CLI

```
gallodoc training export-pairs \
  --input <envelope_or_relationships.json> \
  --out <pairs.jsonl> \
  [--seed 42] \
  [--ratios 0.8,0.1,0.1] \
  [--include-hard-negatives]
```

Behavior:

- Reads `--input`. If the input is a v3 envelope (has `schema_version`),
  pairs are extracted from `envelope.relationships`. If the input is a
  JSON array, each element is treated as an envelope and pairs are
  extracted from each.
- If `--include-hard-negatives` is set, the four hard-negative
  strategies run and their pairs are appended to the output.
- `assert_pairs_clean` runs over the full pair list. The export aborts
  on any leak.
- If `--ratios` is given (default form: `0.8,0.1,0.1`), the splitter
  partitions the pairs and three files are written:
  `<out>.train.jsonl`, `<out>.dev.jsonl`, `<out>.test.jsonl`.
- If `--ratios` is omitted, a single `<out>` is written (the `--out`
  argument is used verbatim) with all pairs.

Exit codes: `0` on success, non-zero on bad input, bad ratios, or
privacy leak. Stderr carries the human-readable error message.

---

## 8. Forward references

- **Prompt 07** consumes the `<out>.train.jsonl` produced by this CLI.
  The trainer reads pairs, filters out `label: "uncertain"`, and uses
  the remaining `match` / `non_match` pairs as supervision signal.
- **Prompt 10** (release-safety gate) runs `gallodoc training
  export-pairs` over the v3 demo dataset as part of the release-cut
  smoke test. A failed safety scan blocks the release.

---

## 9. Open items (non-blocking)

The following choices are deferred to prompt 07 / prompt 10:

- **Minimum corpus size:** documented but not enforced here. Prompt 07
  recommends ≥ 10k pairs with ≥ 2k confirmed positives.
- **Per-source pair weighting:** the `discovered_by` field is preserved
  so prompt 07's loss function can re-weight (e.g. up-weight
  human-authored, down-weight linker-confirmed). The exporter does not
  apply weights itself.
- **`him_c_certified` flag on the pair record:** the consolidated v3
  `trust` block carries certification status at envelope level rather
  than per-pair. The exporter is not the right place to surface this —
  prompt 07 can join against the source envelope by `gallodoc_ref` if
  needed.
