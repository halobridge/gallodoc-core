# AI usage ledger

`gallodoc.ai_usage` is the open-source helper layer for the GalloDoc Core
v1 `ai_usage` section. It records per-call provider / model / token / cost /
latency data and a hashes-only summary that ships with every projected
envelope.

## What it stores

| Field | Type | Notes |
|---|---|---|
| `run_id` | string | Caller-supplied identifier. |
| `operation` | enum | `classification`, `extraction`, `qa`, `verification`, `embedding`, `ocr_correction`, `policy_check`, `summary`, `custom`. |
| `provider` | enum | `openai`, `anthropic`, `google`, `azure_openai`, `ollama`, `local`, `custom`. |
| `model` | string | Provider model id. |
| `input_tokens`, `output_tokens`, `total_tokens` | integer | |
| `estimated_cost`, `currency` | number / string | |
| `latency_ms` | integer | |
| `status` | enum | `success`, `failed`, `skipped`, `partial`. |
| `retry_count` | integer | |
| `started_at`, `completed_at` | string | ISO 8601. |
| `data_mode` | enum | `raw_internal`, `redacted`, `masked`, `synthetic`, `full_internal`. |
| `purpose` | string | Free-form short label. |
| `prompt_hash`, `response_hash` | string | sha256-prefixed. |
| `stored_prompt`, `stored_response` | boolean | True only when the originating system retained the body internally. |

## What it does NOT store

* Raw prompt bodies.
* Raw response bodies.
* Tool outputs / tool call payloads.
* Provider-specific raw HTTP bodies.
* User identifiers, tenant ids, or session hashes.

## Helpers

```python
from gallodoc.ai_usage import (
    add_ai_run,
    empty_ai_usage,
    estimate_cost,
    hash_text,
    summarize_ai_usage,
)

usage = empty_ai_usage()
usage = add_ai_run(
    usage,
    run_id="run-001",
    operation="extraction",
    provider="openai",
    model="gpt-4o-2024-08-06",
    input_tokens=1820,
    output_tokens=410,
    estimated_cost=estimate_cost("openai", "gpt-4o", 1820, 410),
    latency_ms=2150,
    prompt_hash=hash_text("…some bounded prompt…"),
    response_hash=hash_text("…some bounded response…"),
)
print(summarize_ai_usage(usage["runs"]))
```

`add_ai_run(...)` is **immutable** — it returns a new block with the
appended run and a freshly recomputed summary. It is safe to chain.

## Cost estimation

`estimate_cost(provider, model, input_tokens, output_tokens, *, pricing_table=None)`
ships a small built-in table with illustrative rates. Production callers
should supply their own table:

```python
my_prices = {
    ("openai", "gpt-4o-2024-08-06"): (0.0025, 0.010),
    ("local", "*"): (0.0, 0.0),
}
cost = estimate_cost("openai", "gpt-4o-2024-08-06", 1000, 500, pricing_table=my_prices)
```

The table is a `(input_per_1k, output_per_1k)` USD rate per
`(provider, model)`. Wildcards are supported via `(provider, "*")`.

## Hashing

`hash_text(text)` returns a `sha256:`-prefixed hex digest. The convention
is: hash the *exact* canonical bytes the originating system sent; do not
re-canonicalize. The hash is the only identifier downstream verifiers need;
the body is intentionally inaccessible from the open-core envelope.

## Privacy invariants

* The `ai_usage` block never carries raw prompts or raw responses, even
  when a HaloBridge runtime stores them internally with
  `HALOBRIDGE_AI_USAGE_STORE_RAW=true`. Internal storage is a separate
  policy decision; the open-core projection always strips it.
* `data_mode` documents how the input was treated: `raw_internal` /
  `redacted` / `masked` / `synthetic` / `full_internal`. Choose honestly —
  consumers will use this field to decide whether the run was
  PHI-conformant.

## See also

* [`gallodoc-core-v1.md`](gallodoc-core-v1.md) — the schema position of
  `ai_usage`.
* [`open-core-vs-enterprise.md`](open-core-vs-enterprise.md) — what
  HaloBridge adds on top of the public ledger.
* [`privacy-and-safety.md`](privacy-and-safety.md) — projection-level
  guarantees.
