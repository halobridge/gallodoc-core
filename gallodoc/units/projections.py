"""Token / model projection helpers for GalloUnits.

Default estimator is a deterministic char-count heuristic
(``ceil(len(text) / 4)``). Optional plugins:

* `tiktoken` (``pip install gallodoc[tokenizer]``) — exact OpenAI tokenizer.
* `transformers` — tokenizer-by-name lookup.

Custom providers can register through :func:`register_token_estimator`.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable

EstimatorFn = Callable[[str, str, str], int]
"""Signature: ``(text, provider, model) -> int``."""

# Provider+model -> estimator function.
_REGISTRY: dict[tuple[str, str], EstimatorFn] = {}

# Default per-provider tokenizer label (for documentation; not enforced).
_DEFAULT_TOKENIZER_LABELS: dict[str, str] = {
    "openai": "o200k_base",
    "anthropic": "anthropic_v2",
    "google": "sentencepiece_v2",
    "azure_openai": "o200k_base",
    "ollama": "model_specific",
    "local": "char_count",
    "custom": "char_count",
}


def register_token_estimator(provider: str, model: str, fn: EstimatorFn) -> None:
    """Register a custom estimator for a (provider, model) pair."""
    _REGISTRY[(provider, model)] = fn


def _char_count_estimator(text: str, provider: str, model: str) -> int:
    if not text:
        return 0
    # ~4 chars per token on average in English; round up.
    return max(1, (len(text) + 3) // 4)


def _tiktoken_estimator(text: str, provider: str, model: str) -> int | None:
    try:
        import tiktoken  # type: ignore  # noqa: PLC0415
    except ImportError:
        return None
    try:
        encoder = tiktoken.encoding_for_model(model)
    except Exception:
        try:
            encoder = tiktoken.get_encoding("o200k_base")
        except Exception:
            return None
    return len(encoder.encode(text))


def estimate_tokens_for_unit(unit: dict[str, Any], provider: str, model: str) -> int:
    """Return an estimated token count for ``unit`` for ``(provider, model)``.

    The estimate is exact when an installed plugin handles the provider/model;
    otherwise it falls back to the deterministic char-count heuristic. The
    GalloUnit's ``content_summary`` is used as the source text — callers who
    have the full unit text available should monkey-patch the unit dict.
    """
    text = str(unit.get("content_summary") or unit.get("text") or "")
    custom = _REGISTRY.get((provider, model))
    if custom is not None:
        try:
            return int(custom(text, provider, model))
        except Exception:
            pass
    if provider in {"openai", "azure_openai"}:
        result = _tiktoken_estimator(text, provider, model)
        if result is not None:
            return int(result)
    return _char_count_estimator(text, provider, model)


def _projection_hash(text: str, provider: str, model: str, tokenizer: str) -> str:
    payload = f"{tokenizer}|{provider}|{model}|{text}".encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def build_model_projection(
    units: list[dict[str, Any]],
    *,
    provider: str,
    model: str,
    tokenizer: str | None = None,
    model_family: str | None = None,
) -> list[dict[str, Any]]:
    """Build per-unit ``model_projections[]`` entries.

    Each unit gets one projection; ``token_count`` is estimated as documented
    above. Verifiers with the same canonical text and tokenizer label can
    recompute ``projection_hash``.
    """
    tokenizer_label = tokenizer or _DEFAULT_TOKENIZER_LABELS.get(provider, "char_count")
    family = model_family or model.split("-")[0] if model else ""
    now = datetime.now(timezone.utc).isoformat()
    out: list[dict[str, Any]] = []
    for idx, unit in enumerate(units, start=1):
        text = str(unit.get("content_summary") or unit.get("text") or "")
        token_count = estimate_tokens_for_unit(unit, provider, model)
        out.append(
            {
                "projection_id": f"proj_{idx:04d}",
                "unit_id": unit.get("unit_id", ""),
                "provider": provider,
                "model_family": family or model,
                "model": model,
                "tokenizer": tokenizer_label,
                "token_count": int(token_count),
                "projection_hash": _projection_hash(text, provider, model, tokenizer_label),
                "created_at": now,
            }
        )
    return out


__all__ = [
    "EstimatorFn",
    "register_token_estimator",
    "estimate_tokens_for_unit",
    "build_model_projection",
]
