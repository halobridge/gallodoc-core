"""End-to-end NL→plan tests for examples/v3_0/aibi/.

For each shipped example, runs the planner on the input NL and compares
the result against the committed plan JSON. Compares modulo
``created_at`` (which is non-deterministic).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.aibi import plan, validate_plan


EXAMPLES_DIR = (
    Path(__file__).parent.parent.parent.parent / "examples" / "v3_0" / "aibi"
)


def _load_input(stub: str) -> str:
    return (EXAMPLES_DIR / f"{stub}_input.txt").read_text(encoding="utf-8").strip()


def _load_envelope(stub: str) -> dict | None:
    p = EXAMPLES_DIR / f"{stub}_envelope.json"
    if not p.exists():
        # alternate naming
        alt = EXAMPLES_DIR / f"{stub}_input_envelope.json"
        if alt.exists():
            return json.loads(alt.read_text(encoding="utf-8"))
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _load_expected_plan(stub: str) -> dict:
    return json.loads((EXAMPLES_DIR / f"{stub}_plan.json").read_text(encoding="utf-8"))


def _compare_modulo_created_at(actual: dict, expected: dict) -> None:
    a = dict(actual)
    e = dict(expected)
    a.pop("created_at", None)
    e.pop("created_at", None)
    assert a == e, f"plan mismatch:\nactual={json.dumps(a, indent=2)}\nexpected={json.dumps(e, indent=2)}"


EXAMPLE_STUBS = [
    "customer_360",
    "invoice_to_employee",
    "website_claim_to_policy",
    "contract_to_salesforce_account",
    "cross_tenant_invoice",
]


@pytest.mark.parametrize("stub", EXAMPLE_STUBS)
def test_example_matches_committed_plan(stub: str) -> None:
    nl = _load_input(stub)
    envelope = _load_envelope(stub)
    p = plan(nl, envelope)
    expected = _load_expected_plan(stub)
    _compare_modulo_created_at(p.to_dict(), expected)


@pytest.mark.parametrize("stub", EXAMPLE_STUBS)
def test_example_plan_passes_validate_plan(stub: str) -> None:
    nl = _load_input(stub)
    envelope = _load_envelope(stub)
    p = plan(nl, envelope)
    validate_plan(p)


def test_cross_tenant_example_has_federation_intersection_check() -> None:
    nl = _load_input("cross_tenant_invoice")
    envelope = _load_envelope("cross_tenant_invoice")
    p = plan(nl, envelope)
    checks = [c.check for c in p.policy_checks]
    assert "federation_intersection" in checks
    fed = next(c for c in p.policy_checks if c.check == "federation_intersection")
    assert set(fed.scopes_allowed or []) == {"fingerprint_only", "trusted_exchange"}


def test_all_example_input_files_exist() -> None:
    for stub in EXAMPLE_STUBS:
        assert (EXAMPLES_DIR / f"{stub}_input.txt").exists(), f"missing {stub}_input.txt"
        assert (EXAMPLES_DIR / f"{stub}_plan.json").exists(), f"missing {stub}_plan.json"


def test_readme_exists() -> None:
    assert (EXAMPLES_DIR / "README.md").exists()
