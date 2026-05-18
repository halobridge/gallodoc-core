"""Tests for apply_relationship_decision — Decision 3 lifecycle helper."""

from __future__ import annotations

import copy

import pytest

from gallodoc.linking.linker import (
    LINKER_DISCOVERED_BY,
    apply_relationship_decision,
    link,
    write_into_envelope,
)

from tests.v3_0.conftest import minimal_v3_envelope


def _seed_envelope_with_linker_entry() -> tuple[dict, str]:
    """Build a v3 envelope with a single linker-suggested entry."""
    src = minimal_v3_envelope()
    src["identity"]["gallodoc_id"] = "doc_src"
    src["gallounits"]["units"] = [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}]
    cand = minimal_v3_envelope()
    cand["identity"]["gallodoc_id"] = "doc_cand"
    cand["gallounits"]["units"] = [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}]
    out = link(src, [cand])
    assert len(out.candidates) == 1
    write_into_envelope(src, out)
    rel_id = out.candidates[0].relationship_id
    return src, rel_id


def test_flip_suggested_to_confirmed_updates_status_and_appends_decision() -> None:
    env, rel_id = _seed_envelope_with_linker_entry()
    apply_relationship_decision(env, rel_id, "confirmed", "ap_lead", rationale="vendor verified")
    entry = env["relationships"]["relationships"][0]
    assert entry["status"] == "confirmed"
    # discovered_by preserved — audit trail shows machine-proposed
    assert entry["discovered_by"] == LINKER_DISCOVERED_BY
    decisions = env["relationships"]["relationship_decisions"]
    assert len(decisions) == 1
    d = decisions[0]
    assert d["relationship_id"] == rel_id
    assert d["verdict"] == "confirmed"
    assert d["decided_by"] == "ap_lead"
    assert d["rationale"] == "vendor verified"
    assert "decided_at" in d
    assert d["decision_id"].startswith("dec_")


def test_flip_suggested_to_rejected_updates_status_and_appends_decision() -> None:
    env, rel_id = _seed_envelope_with_linker_entry()
    apply_relationship_decision(env, rel_id, "rejected", "him_c_certified_reviewer")
    entry = env["relationships"]["relationships"][0]
    assert entry["status"] == "rejected"
    assert entry["discovered_by"] == LINKER_DISCOVERED_BY
    decisions = env["relationships"]["relationship_decisions"]
    assert len(decisions) == 1
    assert decisions[0]["verdict"] == "rejected"
    assert decisions[0]["decided_by"] == "him_c_certified_reviewer"
    # Optional rationale defaults to empty string
    assert decisions[0]["rationale"] == ""


def test_idempotent_reapplying_same_verdict_is_noop() -> None:
    env, rel_id = _seed_envelope_with_linker_entry()
    apply_relationship_decision(env, rel_id, "confirmed", "ap_lead")
    after_first = copy.deepcopy(env)
    apply_relationship_decision(env, rel_id, "confirmed", "ap_lead")
    # No new decision record was appended
    assert env["relationships"]["relationship_decisions"] == after_first["relationships"]["relationship_decisions"]
    assert env["relationships"]["relationships"][0]["status"] == "confirmed"


def test_invalid_verdict_raises_value_error() -> None:
    env, rel_id = _seed_envelope_with_linker_entry()
    with pytest.raises(ValueError, match="verdict"):
        apply_relationship_decision(env, rel_id, "maybe", "ap_lead")
    with pytest.raises(ValueError, match="verdict"):
        apply_relationship_decision(env, rel_id, "suggested", "ap_lead")
    with pytest.raises(ValueError, match="verdict"):
        apply_relationship_decision(env, rel_id, "", "ap_lead")


def test_missing_relationship_id_raises_value_error() -> None:
    env, _rel_id = _seed_envelope_with_linker_entry()
    with pytest.raises(ValueError, match="not found"):
        apply_relationship_decision(env, "rel_nonexistent", "confirmed", "ap_lead")


def test_decision_record_carries_all_required_fields() -> None:
    env, rel_id = _seed_envelope_with_linker_entry()
    apply_relationship_decision(env, rel_id, "confirmed", "ap_lead", rationale="ok")
    d = env["relationships"]["relationship_decisions"][0]
    for key in ("decision_id", "relationship_id", "verdict", "decided_by", "decided_at", "rationale"):
        assert key in d, f"missing {key!r} in decision record: {d}"


def test_flip_from_confirmed_to_rejected_works() -> None:
    """A re-decision (confirmed → rejected) is allowed and appends another record."""
    env, rel_id = _seed_envelope_with_linker_entry()
    apply_relationship_decision(env, rel_id, "confirmed", "ap_lead")
    apply_relationship_decision(env, rel_id, "rejected", "him_c_certified_reviewer", rationale="invalidated")
    entry = env["relationships"]["relationships"][0]
    assert entry["status"] == "rejected"
    decisions = env["relationships"]["relationship_decisions"]
    assert len(decisions) == 2
    assert decisions[0]["verdict"] == "confirmed"
    assert decisions[1]["verdict"] == "rejected"


def test_apply_decision_with_non_object_relationships_raises() -> None:
    env = minimal_v3_envelope()
    env["relationships"] = []  # bare-array shape, not v3 object
    with pytest.raises(ValueError, match="relationships"):
        apply_relationship_decision(env, "rel_xyz", "confirmed", "ap_lead")
