# Training Lab — Worked Example

This directory shows the embedder training lab (Codex 06) end-to-end on
a small synthetic corpus.

## Files

| File | Purpose |
|---|---|
| [`input_envelopes.json`](input_envelopes.json) | Four synthetic v3 envelopes: one invoice with curated relationships, a second invoice for the vendor-match negative, and two employee records that play the approver / wrong-approver roles. |
| [`output_pairs.jsonl`](output_pairs.jsonl) | Result of `gallodoc training export-pairs` with **no** hard negatives. |
| [`output_pairs_with_hard_negatives.jsonl`](output_pairs_with_hard_negatives.jsonl) | Same, with `--include-hard-negatives`. Demonstrates all four strategies firing. |
| [`output_pairs.train.jsonl`](output_pairs.train.jsonl) | The 80% train slice from a deterministic `seed=42`, ratios `0.8/0.1/0.1` split. |
| [`output_pairs.dev.jsonl`](output_pairs.dev.jsonl) | The 10% dev slice (empty on this tiny corpus). |
| [`output_pairs.test.jsonl`](output_pairs.test.jsonl) | The 10% test slice. |

The `created_at` field on every emitted pair is normalized to
`2026-05-16T12:00:00Z` for example-file reproducibility. In a real run
the exporter stamps the current UTC time.

## Walk-through

### `input_envelopes.json` — what's in the corpus

The headline envelope (`doc_invoice_001`) carries four relationship entries:

1. **`rel_inv001_emp042_confirmed_human`** — `status: "confirmed"`,
   `discovered_by: "human_review"`. Human-authored positive.
2. **`rel_inv001_emp099_confirmed_linker`** — `status: "confirmed"`,
   `discovered_by: "gallodoc-linker/3.0.0"`. **Linker-discovered,
   human-confirmed positive** — Decision 3's highest-quality
   supervision signal. The exporter does **not** filter this out.
3. **`rel_inv001_emp123_rejected`** — `status: "rejected"`,
   `discovered_by: "gallodoc-linker/3.0.0"`, with a matching
   `relationship_decisions[]` rejection record. Real negative.
4. **`rel_inv001_inv002_suggested`** — `status: "suggested"`, no
   decision yet. Exported as `uncertain` for downstream curation.

### `output_pairs.jsonl` — the basic exporter result

Four pairs come out — one per relationship entry — with the following
labels:

| pair_id (prefix) | label | discovered_by |
|---|---|---|
| `rel_inv001_emp042_...` | `match` | `human_review` |
| `rel_inv001_emp099_...` | `match` | `gallodoc-linker/3.0.0` |
| `rel_inv001_emp123_...` | `non_match` | `gallodoc-linker/3.0.0` |
| `rel_inv001_inv002_...` | `uncertain` | `gallodoc-linker/3.0.0` |

The second row is the load-bearing one: a linker-suggested,
human-confirmed positive ends up in the training set as a `match`,
with `discovered_by` carried through verbatim.

### `output_pairs_with_hard_negatives.jsonl` — adding the four strategies

With `--include-hard-negatives`, the four deterministic strategies fire
on this corpus:

- **`same_org_wrong_person`** — both employee records share
  `source.source_system: "demo_hr"`. The pair `(doc_employee_042,
  doc_employee_099)` is emitted as `non_match`.
- **`same_vendor_wrong_invoice`** — both invoices declare
  `truth_ledger.claims[]` with `field_path == "vendor_name"` →
  `"Acme Co"`. The pair `(doc_invoice_001, doc_invoice_002)` is emitted
  as `non_match`.
- **`similar_clause_different_obligation`** — the two employee records
  share the `person` semantic role and have disjoint (empty) claim
  sets, which counts as "different obligations" under the strategy.
  Emitted as `non_match`.
- **`same_customer_name_different_domain`** — the
  `doc_employee_042` content_summary mentions "Acme" and lives in
  `demo_hr`; both invoices mention "Acme" and live in `demo_ap`. The
  cross-domain pairs are emitted as `non_match`.

### `output_pairs.train.jsonl` / `.dev.jsonl` / `.test.jsonl`

The deterministic splitter assigns each `pair_id` to a fixed bucket
modulo 1000 (salted with the seed). On this tiny 4-pair corpus the
splits are uneven (3 / 0 / 1) — the splitter still produces the
**same** assignment on every run, which is the property prompt 07's
training loop relies on.

## Re-running the example

```bash
# Basic
gallodoc training export-pairs \
  --input examples/v3_0/training/input_envelopes.json \
  --out /tmp/pairs.jsonl

# With hard negatives
gallodoc training export-pairs \
  --input examples/v3_0/training/input_envelopes.json \
  --out /tmp/pairs_with_hn.jsonl \
  --include-hard-negatives

# 80/10/10 split (writes /tmp/pairs.train.jsonl + .dev.jsonl + .test.jsonl)
gallodoc training export-pairs \
  --input examples/v3_0/training/input_envelopes.json \
  --out /tmp/pairs.jsonl \
  --ratios 0.8,0.1,0.1
```

`created_at` on a fresh run will be the current UTC time; everything
else matches byte-for-byte.
