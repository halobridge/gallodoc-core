"""End-to-end demo: every JSON fixture in the full operational intelligence
reference loads and validates correctly.

This test asserts on the structural properties of the six demo files in
``examples/v3_0/full_operational_intelligence_reference/`` and the AI/BI
plan/receipt they include. It is the canonical "every Codex 01-09
contribution survives integration" gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.aibi.query_model import SAFE_QUERY_TYPES
from gallodoc.aibi.safe_filters import assert_plan_is_safe
from gallodoc.projection.safety import assert_no_enterprise_leakage
from gallodoc.validation import validate_envelope


PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEMO_DIR = PACKAGE_ROOT / "examples" / "v3_0" / "full_operational_intelligence_reference"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(name: str) -> dict:
    return json.loads((DEMO_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_demo_directory_present() -> None:
    assert DEMO_DIR.is_dir(), f"Demo directory missing: {DEMO_DIR}"
    expected = {
        "vendor_invoice.gdoc.json",
        "employee_record.gdoc.json",
        "linker_output.json",
        "linker_output_with_embeddings.json",
        "human_review_decision.json",
        "aibi_query_receipt.json",
        "README.md",
    }
    present = {p.name for p in DEMO_DIR.iterdir()}
    missing = expected - present
    assert not missing, f"Missing demo files: {missing}"


@pytest.mark.parametrize("name", [
    "vendor_invoice.gdoc.json",
    "employee_record.gdoc.json",
    "human_review_decision.json",
])
def test_envelope_validates(name: str) -> None:
    env = _load(name)
    assert env.get("schema_version") == "gallodoc-core/v3"
    result = validate_envelope(env)
    assert result.valid, f"{name} failed v3 validation: {result.issues}"


@pytest.mark.parametrize("name", [
    "vendor_invoice.gdoc.json",
    "employee_record.gdoc.json",
    "human_review_decision.json",
])
def test_envelope_passes_privacy_scan(name: str) -> None:
    env = _load(name)
    # Raises on leakage; this assertion is the contract.
    assert_no_enterprise_leakage(env)


def test_linker_output_loads_and_is_pinned_to_suggested() -> None:
    payload = _load("linker_output.json")
    candidates = payload.get("candidates") or []
    assert candidates, "linker_output.json has no candidates"
    for c in candidates:
        assert c.get("status") == "suggested", (
            f"linker candidate {c.get('relationship_id')!r} must have "
            f"status='suggested', got {c.get('status')!r}"
        )
        discovered_by = c.get("discovered_by") or ""
        assert "linker" in discovered_by.lower(), (
            f"linker candidate must have discovered_by ~ *linker*, got "
            f"{discovered_by!r}"
        )


def test_linker_output_with_embeddings_loads() -> None:
    payload = _load("linker_output_with_embeddings.json")
    candidates = payload.get("candidates") or []
    assert candidates, "linker_output_with_embeddings.json has no candidates"
    for c in candidates:
        assert c.get("status") == "suggested"
        assert "linker" in (c.get("discovered_by") or "").lower()


def test_human_review_decision_promotes_relationship_to_confirmed() -> None:
    env = _load("human_review_decision.json")
    rels_block = env.get("relationships") or {}
    rels = rels_block.get("relationships") or []
    decisions = rels_block.get("relationship_decisions") or []
    assert rels, "human_review_decision envelope must carry the linker-suggested relationship"
    # At least one entry was discovered by the linker AND is now confirmed.
    confirmed_linker = [
        r for r in rels
        if "linker" in (r.get("discovered_by") or "").lower()
        and r.get("status") == "confirmed"
    ]
    assert confirmed_linker, (
        "no relationship discovered_by ~ *linker* with status='confirmed' "
        "found in human_review_decision.json"
    )
    # And a matching relationship_decisions[] entry exists.
    decided_ids = {d.get("relationship_id") for d in decisions if isinstance(d, dict)}
    for r in confirmed_linker:
        rel_id = r.get("relationship_id")
        assert rel_id in decided_ids, (
            f"confirmed linker relationship {rel_id!r} missing matching "
            "relationship_decisions[] record"
        )


def test_aibi_plan_validates() -> None:
    payload = _load("aibi_query_receipt.json")
    plan_dict = payload.get("plan")
    assert isinstance(plan_dict, dict), "aibi_query_receipt.json missing 'plan' object"
    # Structural checks: every plan must declare its safe_query_type, carry
    # a plan_id, declare filters, and declare policy_checks.
    assert plan_dict.get("plan_id"), "plan missing plan_id"
    assert plan_dict.get("safe_query_type") in SAFE_QUERY_TYPES, (
        f"plan.safe_query_type {plan_dict.get('safe_query_type')!r} "
        f"not in SAFE_QUERY_TYPES {SAFE_QUERY_TYPES}"
    )
    assert isinstance(plan_dict.get("filters"), list), "plan.filters must be a list"
    assert isinstance(plan_dict.get("policy_checks"), list), "plan.policy_checks must be a list"
    # No-raw-SQL invariant: no string in the plan may contain SQL escape
    # characters or DML keywords. Reuse the walker pattern from
    # gallodoc.aibi.safe_filters but at the dict level (the planner emits
    # a dict here).
    _SQL_FORBIDDEN = ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", ";", "`", "--", "/*", "*/")

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            upper = node.upper()
            for tok in _SQL_FORBIDDEN:
                if tok in upper:
                    raise AssertionError(
                        f"unsafe plan: {path}={node!r} contains forbidden token {tok!r}"
                    )

    walk(plan_dict, "plan")


def test_aibi_receipt_present() -> None:
    payload = _load("aibi_query_receipt.json")
    receipt = payload.get("receipt")
    assert isinstance(receipt, dict), "aibi_query_receipt.json missing 'receipt' object"
    # Receipts MUST carry plan_id + receipt_id at minimum.
    assert receipt.get("plan_id"), "receipt missing plan_id"
    assert receipt.get("receipt_id"), "receipt missing receipt_id"
    # The plan and receipt must reference the same plan_id.
    assert receipt["plan_id"] == payload["plan"]["plan_id"], (
        "receipt.plan_id does not match plan.plan_id"
    )
