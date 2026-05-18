"""Tests for the four hard-negative strategies."""

from __future__ import annotations

import copy
from typing import Any

from gallodoc.training.hard_negatives import (
    STRATEGIES,
    _PER_GROUP_CAP,
    generate_hard_negatives,
)


def _env(
    gid: str,
    *,
    source_system: str = "synthetic",
    document_type: str = "document",
    semantic_roles: list[str] | None = None,
    claim_paths: list[str] | None = None,
    vendor_name: str | None = None,
    unit_summaries: list[str] | None = None,
) -> dict[str, Any]:
    units: list[dict[str, Any]] = []
    for role in semantic_roles or []:
        units.append({"semantic_role": role, "content_summary": ""})
    for summary in unit_summaries or []:
        units.append({"semantic_role": "context", "content_summary": summary})

    claims = []
    for fp in claim_paths or []:
        claims.append({"field_path": fp, "value": ""})
    if vendor_name is not None:
        claims.append({"field_path": "vendor_name", "value": vendor_name})

    return {
        "schema_version": "gallodoc-core/v3",
        "identity": {
            "gallodoc_id": gid,
            "document_type": document_type,
        },
        "source": {
            "source_system": source_system,
        },
        "gallounits": {
            "unit_strategy": "gallounit_v1",
            "units": units,
        },
        "truth_ledger": {
            "available": True,
            "claims": claims,
            "events": [],
            "truth_state": "uncertified",
        },
    }


# ---------------------------------------------------------------------------
# Strategy 1: same_org_wrong_person
# ---------------------------------------------------------------------------


def test_same_org_wrong_person_fires_on_employee_envelopes() -> None:
    envs = [
        _env("p1", source_system="hr_system", document_type="employee_record"),
        _env("p2", source_system="hr_system", document_type="employee_record"),
    ]
    pairs = generate_hard_negatives(envs, strategies=["same_org_wrong_person"])
    assert len(pairs) == 1
    assert pairs[0].label == "non_match"
    assert pairs[0].discovered_by == "hard_negative:same_org_wrong_person"
    assert {pairs[0].source_gallodoc_ref, pairs[0].target_gallodoc_ref} == {"p1", "p2"}


def test_same_org_wrong_person_does_not_cross_orgs() -> None:
    envs = [
        _env("p1", source_system="hr_a", document_type="person_record"),
        _env("p2", source_system="hr_b", document_type="person_record"),
    ]
    pairs = generate_hard_negatives(envs, strategies=["same_org_wrong_person"])
    assert pairs == []


def test_same_org_wrong_person_skips_non_person_docs() -> None:
    envs = [
        _env("p1", source_system="hr", document_type="invoice"),
        _env("p2", source_system="hr", document_type="invoice"),
    ]
    pairs = generate_hard_negatives(envs, strategies=["same_org_wrong_person"])
    assert pairs == []


# ---------------------------------------------------------------------------
# Strategy 2: same_vendor_wrong_invoice
# ---------------------------------------------------------------------------


def test_same_vendor_wrong_invoice_fires() -> None:
    envs = [
        _env("inv1", document_type="invoice", vendor_name="Acme Co"),
        _env("inv2", document_type="invoice", vendor_name="Acme Co"),
    ]
    pairs = generate_hard_negatives(envs, strategies=["same_vendor_wrong_invoice"])
    assert len(pairs) == 1
    assert pairs[0].discovered_by == "hard_negative:same_vendor_wrong_invoice"


def test_same_vendor_wrong_invoice_skips_different_vendors() -> None:
    envs = [
        _env("inv1", document_type="invoice", vendor_name="Acme Co"),
        _env("inv2", document_type="invoice", vendor_name="Globex Corp"),
    ]
    pairs = generate_hard_negatives(envs, strategies=["same_vendor_wrong_invoice"])
    assert pairs == []


def test_same_vendor_wrong_invoice_skips_non_invoice_docs() -> None:
    envs = [
        _env("doc1", document_type="contract", vendor_name="Acme Co"),
        _env("doc2", document_type="contract", vendor_name="Acme Co"),
    ]
    pairs = generate_hard_negatives(envs, strategies=["same_vendor_wrong_invoice"])
    assert pairs == []


# ---------------------------------------------------------------------------
# Strategy 3: similar_clause_different_obligation
# ---------------------------------------------------------------------------


def test_similar_clause_different_obligation_fires() -> None:
    envs = [
        _env(
            "c1",
            semantic_roles=["payment_terms"],
            claim_paths=["net_terms_days"],
        ),
        _env(
            "c2",
            semantic_roles=["payment_terms"],
            claim_paths=["late_fee_percent"],
        ),
    ]
    pairs = generate_hard_negatives(
        envs, strategies=["similar_clause_different_obligation"]
    )
    assert len(pairs) == 1
    assert pairs[0].discovered_by == "hard_negative:similar_clause_different_obligation"


def test_similar_clause_with_overlapping_claims_is_not_generated() -> None:
    envs = [
        _env(
            "c1",
            semantic_roles=["payment_terms"],
            claim_paths=["net_terms_days"],
        ),
        _env(
            "c2",
            semantic_roles=["payment_terms"],
            claim_paths=["net_terms_days"],  # overlapping
        ),
    ]
    pairs = generate_hard_negatives(
        envs, strategies=["similar_clause_different_obligation"]
    )
    assert pairs == []


def test_similar_clause_with_no_shared_role_is_not_generated() -> None:
    envs = [
        _env(
            "c1",
            semantic_roles=["payment_terms"],
            claim_paths=["net_terms_days"],
        ),
        _env(
            "c2",
            semantic_roles=["delivery_terms"],
            claim_paths=["late_fee_percent"],
        ),
    ]
    pairs = generate_hard_negatives(
        envs, strategies=["similar_clause_different_obligation"]
    )
    assert pairs == []


# ---------------------------------------------------------------------------
# Strategy 4: same_customer_name_different_domain
# ---------------------------------------------------------------------------


def test_same_customer_name_different_domain_fires() -> None:
    envs = [
        _env(
            "d1",
            source_system="hospital_a",
            unit_summaries=["Patient referred from Acme Health"],
        ),
        _env(
            "d2",
            source_system="hospital_b",
            unit_summaries=["Acme Insurance pre-auth pending"],
        ),
    ]
    pairs = generate_hard_negatives(
        envs, strategies=["same_customer_name_different_domain"]
    )
    assert len(pairs) == 1
    assert (
        pairs[0].discovered_by
        == "hard_negative:same_customer_name_different_domain"
    )


def test_same_customer_name_skips_when_systems_match() -> None:
    envs = [
        _env(
            "d1",
            source_system="hospital_a",
            unit_summaries=["Patient referred from Acme Health"],
        ),
        _env(
            "d2",
            source_system="hospital_a",  # same system — disqualified
            unit_summaries=["Acme Insurance pre-auth pending"],
        ),
    ]
    pairs = generate_hard_negatives(
        envs, strategies=["same_customer_name_different_domain"]
    )
    assert pairs == []


def test_same_customer_name_skips_when_no_shared_token() -> None:
    envs = [
        _env(
            "d1",
            source_system="a",
            unit_summaries=["Acme Health referral"],
        ),
        _env(
            "d2",
            source_system="b",
            unit_summaries=["Wonka Bar inventory"],
        ),
    ]
    pairs = generate_hard_negatives(
        envs, strategies=["same_customer_name_different_domain"]
    )
    assert pairs == []


# ---------------------------------------------------------------------------
# Shared invariants
# ---------------------------------------------------------------------------


def test_strategies_set_matches_documented_four() -> None:
    assert set(STRATEGIES) == {
        "same_org_wrong_person",
        "same_vendor_wrong_invoice",
        "similar_clause_different_obligation",
        "same_customer_name_different_domain",
    }


def test_default_runs_all_four_strategies() -> None:
    envs = [
        _env(
            "p1",
            source_system="hr_system",
            document_type="employee_record",
        ),
        _env(
            "p2",
            source_system="hr_system",
            document_type="employee_record",
        ),
        _env("inv1", document_type="invoice", vendor_name="Acme Co"),
        _env("inv2", document_type="invoice", vendor_name="Acme Co"),
        _env(
            "c1",
            semantic_roles=["payment_terms"],
            claim_paths=["net_terms_days"],
        ),
        _env(
            "c2",
            semantic_roles=["payment_terms"],
            claim_paths=["late_fee_percent"],
        ),
        _env(
            "d1",
            source_system="hospital_a",
            unit_summaries=["Patient referred from Acme Health"],
        ),
        _env(
            "d2",
            source_system="hospital_b",
            unit_summaries=["Acme Insurance pre-auth pending"],
        ),
    ]
    pairs = generate_hard_negatives(envs)
    by_strategy = {}
    for p in pairs:
        strat = p.discovered_by.split(":", 1)[1]
        by_strategy.setdefault(strat, []).append(p)
    # Each strategy fires at least once.
    for strat in (
        "same_org_wrong_person",
        "same_vendor_wrong_invoice",
        "similar_clause_different_obligation",
        "same_customer_name_different_domain",
    ):
        assert strat in by_strategy, f"strategy {strat!r} did not fire"


def test_no_candidates_returns_empty_list() -> None:
    envs = [_env("only_one", document_type="memo")]
    pairs = generate_hard_negatives(envs)
    assert pairs == []


def test_all_outputs_have_non_match_and_hard_negative_prefix() -> None:
    envs = [
        _env(
            "p1",
            source_system="hr_system",
            document_type="employee_record",
        ),
        _env(
            "p2",
            source_system="hr_system",
            document_type="employee_record",
        ),
    ]
    pairs = generate_hard_negatives(envs)
    for p in pairs:
        assert p.label == "non_match"
        assert p.discovered_by.startswith("hard_negative:")
        assert p.confidence == 0.0
        assert p.reviewer_decision is None
        assert p.evidence_refs == []
        assert p.semantic_intent is None


def test_deterministic_across_runs() -> None:
    envs = [
        _env(
            "p1",
            source_system="hr_system",
            document_type="employee_record",
        ),
        _env(
            "p2",
            source_system="hr_system",
            document_type="employee_record",
        ),
        _env(
            "p3",
            source_system="hr_system",
            document_type="employee_record",
        ),
    ]
    a = generate_hard_negatives(copy.deepcopy(envs))
    b = generate_hard_negatives(copy.deepcopy(envs))
    assert [p.pair_id for p in a] == [p.pair_id for p in b]


def test_per_group_cap_is_enforced() -> None:
    """11 employees in one org → 10 pairs (cap at _PER_GROUP_CAP)."""
    envs = [
        _env(
            f"p{i:02d}",
            source_system="hr_system",
            document_type="employee_record",
        )
        for i in range(11)
    ]
    pairs = generate_hard_negatives(envs, strategies=["same_org_wrong_person"])
    assert len(pairs) == _PER_GROUP_CAP
    assert _PER_GROUP_CAP == 10
