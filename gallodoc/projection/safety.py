"""Privacy assertions for v3 envelopes.

Used by:
  - tests/v3_0/ for regression coverage
  - The forward-referenced scripts/release_safety_gate.py in prompt 10
  - .github/workflows/v3-release.yml (already imports this with a fallback)
"""

from __future__ import annotations

import re
from typing import Any

from gallodoc.projection.forbidden import EXTENSIONS_HALOBRIDGE_BANNED


_PLATFORM_INTERNAL_KEYS: frozenset[str] = frozenset({
    "policy_formula",
    "halobridge_internal",
    "__internal__",
})

_LEAK_PATTERNS: dict[str, re.Pattern] = {
    "SSN-like":     re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "MRN-like":     re.compile(r"\bMRN[: ]+[A-Z0-9]{6,}\b"),
    "private_key":  re.compile(r"\b(private_key|signing_key|raw_signature|PRIVATE_PEM)\b"),
}


class EnterpriseLeakageError(AssertionError):
    """Raised when a v3 envelope contains enterprise/platform leakage."""


def assert_no_enterprise_leakage(envelope: dict[str, Any]) -> None:
    """Raise EnterpriseLeakageError if the envelope contains enterprise leakage.

    Checks:
      - No platform-internal keys (policy_formula, halobridge_internal, __internal__) anywhere.
      - No surviving extensions.halobridge.<banned> keys.
      - No SSN-like / MRN-like / private-key-shaped strings.
    """
    leaks: list[str] = []

    # Walk the tree for forbidden key names + leak patterns.
    def walk(node: Any, path: str = "$") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in _PLATFORM_INTERNAL_KEYS:
                    leaks.append(f"{path}.{k}: platform-internal key {k!r}")
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, item in enumerate(node[:512]):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            for label, pat in _LEAK_PATTERNS.items():
                if pat.search(node):
                    leaks.append(f"{path}: {label} string detected")
                    break  # one label per string is enough

    walk(envelope)

    # Banned extensions.halobridge.<known_block> keys (Decision 4 + Q5 fix).
    halo = (envelope.get("extensions") or {}).get("halobridge") or {}
    if isinstance(halo, dict):
        hit = sorted(set(halo) & EXTENSIONS_HALOBRIDGE_BANNED)
        for name in hit:
            leaks.append(f"$.extensions.halobridge.{name}: banned (Decision 4 / Q5 fix)")

    if leaks:
        raise EnterpriseLeakageError(
            f"enterprise leakage detected ({len(leaks)} issue(s)):\n  - " + "\n  - ".join(leaks)
        )


__all__ = ["assert_no_enterprise_leakage", "EnterpriseLeakageError"]
