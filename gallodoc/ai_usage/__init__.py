"""GalloDoc open-core AI usage ledger helpers.

The ledger captures per-call provider / model / token / cost / latency data.
Raw prompts and raw responses are NEVER stored in the open-core ledger; only
``prompt_hash`` and ``response_hash`` survive. The ``stored_prompt`` and
``stored_response`` flags record whether HaloBridge (or any other origin
system) retained the body internally.

Functions:

* :func:`empty_ai_usage` — return an empty, schema-shaped block.
* :func:`add_ai_run` — append a run, returning a new block (immutable update).
* :func:`summarize_ai_usage` — recompute the aggregate summary from a list of
  runs.
* :func:`estimate_cost` — best-effort per-token cost estimate. The pricing
  table is illustrative; production callers should supply their own.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable

VALID_OPERATIONS = frozenset(
    {"classification", "extraction", "qa", "verification", "embedding", "ocr_correction", "policy_check", "summary", "custom"}
)
VALID_PROVIDERS = frozenset(
    {"openai", "anthropic", "google", "azure_openai", "ollama", "local", "custom"}
)
VALID_STATUSES = frozenset({"success", "failed", "skipped", "partial"})
VALID_DATA_MODES = frozenset(
    {"raw_internal", "redacted", "masked", "synthetic", "full_internal"}
)

# Illustrative prices in USD per 1k tokens. Override per-provider with custom
# tables in production. We are not in the business of pricing oracles.
_DEFAULT_PRICES: dict[tuple[str, str], tuple[float, float]] = {
    ("openai", "gpt-4o"): (0.0025, 0.010),
    ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("anthropic", "claude-opus-4-7"): (0.003, 0.015),
    ("anthropic", "claude-sonnet-4-6"): (0.0008, 0.004),
    ("google", "gemini-1.5-pro"): (0.0035, 0.0105),
    # Local / open models default to free.
    ("local", "*"): (0.0, 0.0),
    ("ollama", "*"): (0.0, 0.0),
}


def empty_ai_usage() -> dict[str, Any]:
    """Return a fresh, schema-shaped, zero-runs ai_usage block."""
    return {
        "summary": {
            "total_runs": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "estimated_total_cost": 0.0,
            "currency": "USD",
        },
        "runs": [],
    }


def estimate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    *,
    pricing_table: dict[tuple[str, str], tuple[float, float]] | None = None,
) -> float:
    """Return an estimated USD cost.

    Looks up ``(provider, model)`` first, then ``(provider, "*")``. Returns
    ``0.0`` if no pricing entry matches — callers are expected to plug their
    own table in production.
    """
    table = pricing_table or _DEFAULT_PRICES
    rates = table.get((provider, model)) or table.get((provider, "*"))
    if rates is None:
        return 0.0
    in_rate, out_rate = rates
    return round((input_tokens / 1000.0) * in_rate + (output_tokens / 1000.0) * out_rate, 6)


def _hash_or_empty(value: Any) -> str:
    if value is None:
        return ""
    s = str(value)
    if not s:
        return ""
    if s.startswith("sha256:"):
        return s[:160]
    if all(c in "0123456789abcdefABCDEF" for c in s) and len(s) >= 32:
        return f"sha256:{s.lower()}"
    return s[:160]


def add_ai_run(
    block: dict[str, Any],
    *,
    run_id: str,
    operation: str,
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    estimated_cost: float | None = None,
    currency: str = "USD",
    latency_ms: int = 0,
    status: str = "success",
    retry_count: int = 0,
    started_at: str | None = None,
    completed_at: str | None = None,
    data_mode: str = "redacted",
    purpose: str = "",
    prompt_hash: str = "",
    response_hash: str = "",
    stored_prompt: bool = False,
    stored_response: bool = False,
    pricing_table: dict[tuple[str, str], tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Append a run to ``block`` and return the *new* block (immutable update).

    The function never accepts raw prompts/responses; supply hashes only.
    Token counts default to 0 so callers can omit them for embeddings or
    skipped operations.
    """
    op = operation if operation in VALID_OPERATIONS else "custom"
    prov = provider if provider in VALID_PROVIDERS else "custom"
    stat = status if status in VALID_STATUSES else "success"
    mode = data_mode if data_mode in VALID_DATA_MODES else "redacted"
    if estimated_cost is None:
        estimated_cost = estimate_cost(prov, model, input_tokens, output_tokens, pricing_table=pricing_table)
    total_tokens = int(input_tokens) + int(output_tokens)
    now = datetime.now(timezone.utc).isoformat()

    run = {
        "run_id": str(run_id)[:128],
        "operation": op,
        "provider": prov,
        "model": str(model)[:128],
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": total_tokens,
        "estimated_cost": float(estimated_cost),
        "currency": str(currency)[:8] or "USD",
        "latency_ms": int(latency_ms),
        "status": stat,
        "retry_count": int(retry_count),
        "started_at": started_at or now,
        "completed_at": completed_at or now,
        "data_mode": mode,
        "purpose": str(purpose)[:128],
        "prompt_hash": _hash_or_empty(prompt_hash),
        "response_hash": _hash_or_empty(response_hash),
        "stored_prompt": bool(stored_prompt),
        "stored_response": bool(stored_response),
    }
    new_block = empty_ai_usage()
    new_block["runs"] = list(block.get("runs") or []) + [run]
    new_block["summary"] = summarize_ai_usage(new_block["runs"])
    return new_block


def summarize_ai_usage(runs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Recompute the aggregate summary from a list of runs."""
    runs = list(runs or [])
    total_in = sum(int(r.get("input_tokens") or 0) for r in runs)
    total_out = sum(int(r.get("output_tokens") or 0) for r in runs)
    total = sum(int(r.get("total_tokens") or 0) for r in runs)
    cost = sum(float(r.get("estimated_cost") or 0.0) for r in runs)
    currencies = {str(r.get("currency") or "USD") for r in runs}
    currency = currencies.pop() if len(currencies) == 1 and currencies else "USD"
    return {
        "total_runs": len(runs),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "total_tokens": total or (total_in + total_out),
        "estimated_total_cost": round(cost, 6),
        "currency": currency,
    }


def hash_text(text: str) -> str:
    """Convenience helper — sha256 of UTF-8 bytes, prefixed ``sha256:``."""
    if text is None:
        return ""
    return f"sha256:{hashlib.sha256(str(text).encode('utf-8')).hexdigest()}"


__all__ = [
    "VALID_OPERATIONS",
    "VALID_PROVIDERS",
    "VALID_STATUSES",
    "VALID_DATA_MODES",
    "empty_ai_usage",
    "estimate_cost",
    "add_ai_run",
    "summarize_ai_usage",
    "hash_text",
]
