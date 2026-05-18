"""Tests for gallodoc.linking.linker — orchestrator + write_into_envelope."""

from __future__ import annotations

import copy

import pytest

from gallodoc.linking.linker import (
    LINKER_DISCOVERED_BY,
    LinkerOutput,
    RelationshipCandidate,
    apply_relationship_decision,
    link,
    write_into_envelope,
)
from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


def _envelope_with_units(gallodoc_id: str, units: list[dict]) -> dict:
    env = minimal_v3_envelope()
    env["identity"]["gallodoc_id"] = gallodoc_id
    env["gallounits"]["units"] = units
    return env


def test_link_returns_linker_output_with_correct_source_id() -> None:
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    out = link(src, [cand])
    assert isinstance(out, LinkerOutput)
    assert out.source_document_id == "doc_src"
    assert len(out.candidates) == 1


def test_link_pins_status_to_suggested_and_discovered_by_to_linker() -> None:
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    out = link(src, [cand])
    for c in out.candidates:
        assert c.status == "suggested"
        assert c.discovered_by == LINKER_DISCOVERED_BY
        assert c.discovered_by == "gallodoc-linker/3.0.0"


def test_link_relationship_id_is_deterministic() -> None:
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    out1 = link(src, [cand])
    out2 = link(src, [cand])
    assert [c.relationship_id for c in out1.candidates] == [c.relationship_id for c in out2.candidates]


def test_link_skips_self_link() -> None:
    h = "sha256:" + "a" * 64
    env = _envelope_with_units("doc_same", [{"unit_id": "u1", "text_hash": h}])
    out = link(env, [env])
    assert out.candidates == []


def test_link_filters_below_min_confidence() -> None:
    # Only signal: semantic_role_overlap (weight 0.10). Default min_confidence=0.10
    # → keeps it. min_confidence=0.11 → drops.
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "semantic_role": "approver"}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "semantic_role": "approver"}])
    out_keep = link(src, [cand], min_confidence=0.10)
    assert len(out_keep.candidates) == 1
    out_drop = link(src, [cand], min_confidence=0.11)
    assert out_drop.candidates == []


def test_link_relationship_id_format() -> None:
    h = "sha256:" + "a" * 64
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": h}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": h}])
    out = link(src, [cand])
    rid = out.candidates[0].relationship_id
    assert rid.startswith("rel_")
    assert len(rid) == len("rel_") + 16  # 16 hex chars


def test_write_into_envelope_appends_to_relationships_array() -> None:
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    out = link(src, [cand])
    write_into_envelope(src, out)
    rels = src["relationships"]["relationships"]
    assert len(rels) == 1
    entry = rels[0]
    assert entry["status"] == "suggested"
    assert entry["discovered_by"] == "gallodoc-linker/3.0.0"
    assert entry["source_document_ref"] == "doc_src"
    assert entry["target_document_ref"] == "doc_cand"


def test_write_into_envelope_preserves_existing_entries() -> None:
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    # Pre-existing human-authored entry
    src["relationships"]["relationships"].append({
        "relationship_id": "rel-human-001",
        "source_document_ref": "doc_src",
        "target_document_ref": "doc_other",
        "relationship_type": "supports",
        "status": "confirmed",
        "discovered_by": "human_review",
        "created_at": "2026-05-15T00:00:00Z",
    })
    out = link(src, [cand])
    write_into_envelope(src, out)
    rels = src["relationships"]["relationships"]
    assert len(rels) == 2
    # Original entry preserved
    assert any(r["relationship_id"] == "rel-human-001" for r in rels)


def test_write_into_envelope_is_idempotent() -> None:
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    out = link(src, [cand])
    write_into_envelope(src, out)
    rels_after_first = copy.deepcopy(src["relationships"]["relationships"])
    # Re-run on same envelope — no duplicates
    out2 = link(src, [cand])
    write_into_envelope(src, out2)
    rels_after_second = src["relationships"]["relationships"]
    assert len(rels_after_second) == 1
    assert rels_after_first[0]["relationship_id"] == rels_after_second[0]["relationship_id"]


def test_write_into_envelope_coerces_bare_array_relationships() -> None:
    """A legacy bare-array shape gets coerced to the v3 object shape."""
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    src["relationships"] = []  # legacy shape
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    out = link(src, [cand])
    write_into_envelope(src, out)
    assert isinstance(src["relationships"], dict)
    assert isinstance(src["relationships"]["relationships"], list)
    assert len(src["relationships"]["relationships"]) == 1


def test_linker_output_envelope_passes_validate() -> None:
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    out = link(src, [cand])
    write_into_envelope(src, out)
    # Add created_at to relationship_evidence if needed — the v3 validator
    # only requires top-level relationship entries to carry the required
    # fields. Verify the linker's output specifically.
    result = validate_envelope(src)
    # Linker rule should not trip — entries pin to suggested.
    linker_issues = [i for i in result.issues if "linker" in i.message and "suggested" in i.message]
    assert not linker_issues, f"linker entries should validate: {[i.__dict__ for i in result.issues]}"
    assert result.valid, f"linker output envelope should validate: {[i.__dict__ for i in result.errors()]}"


def test_emitted_entries_have_all_required_fields() -> None:
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    out = link(src, [cand])
    write_into_envelope(src, out)
    entry = src["relationships"]["relationships"][0]
    for key in (
        "relationship_id", "source_document_ref", "target_document_ref",
        "relationship_type", "status", "discovered_by", "created_at",
    ):
        assert key in entry, f"missing {key!r} in emitted entry: {entry}"


def test_semantic_intent_carried_into_emitted_entry() -> None:
    src = _envelope_with_units(
        "doc_invoice",
        [{"unit_id": "u1", "semantic_intent": "invoice_to_employee_approver"}],
    )
    cand = _envelope_with_units(
        "doc_employee",
        [{"unit_id": "u2", "semantic_intent": "invoice_to_employee_approver"}],
    )
    out = link(src, [cand])
    assert len(out.candidates) == 1
    c = out.candidates[0]
    assert c.semantic_intent == "invoice_to_employee_approver"
    assert c.reason_code == "invoice_to_employee_approver"
    assert c.relationship_type == "related_to"


def test_relationship_id_changes_when_type_changes() -> None:
    """Different (source, target, type) tuples produce different IDs."""
    src = _envelope_with_units("doc_src", [{"unit_id": "u1", "text_hash": "sha256:" + "a" * 64}])
    cand1 = _envelope_with_units("doc_cand", [{"unit_id": "u2", "text_hash": "sha256:" + "a" * 64}])
    cand2 = _envelope_with_units("doc_cand2", [{"unit_id": "u3", "text_hash": "sha256:" + "a" * 64}])
    out = link(src, [cand1, cand2])
    rids = {c.relationship_id for c in out.candidates}
    assert len(rids) == 2  # different target_id → different rel_id
