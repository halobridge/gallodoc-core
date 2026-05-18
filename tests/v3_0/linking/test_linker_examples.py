"""Smoke-test the example envelopes under examples/v3_0/linking/.

Loads the fixture pair, runs the linker, and asserts the produced
output matches the stored ``linker_output.json`` structurally. Then
runs ``write_into_envelope`` and ``apply_relationship_decision`` and
asserts those match the stored fixtures.

Volatile fields (``created_at``, ``decided_at``, ``decision_id``) are
ignored — they're timestamp / hash-of-timestamp values that change per
run.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gallodoc.linking.linker import (
    apply_relationship_decision,
    link,
    write_into_envelope,
)
from gallodoc.validation import validate_envelope


EXAMPLES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "examples"
    / "v3_0"
    / "linking"
)


def _load(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text())


def _strip_volatile(obj):
    """Recursively drop fields that change per run (timestamps, decision_ids)."""
    VOLATILE = {"created_at", "decided_at", "decision_id"}
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [_strip_volatile(x) for x in obj]
    return obj


def test_link_on_examples_matches_stored_linker_output() -> None:
    source = _load("source_envelope.json")
    candidate = _load("candidate_envelope.json")
    out = link(source, [candidate])

    actual = {
        "source_document_id": out.source_document_id,
        "candidates": [c.to_dict() for c in out.candidates],
    }
    expected = _load("linker_output.json")
    assert _strip_volatile(actual) == _strip_volatile(expected)


def test_write_into_envelope_on_examples_matches_stored() -> None:
    source = _load("source_envelope.json")
    candidate = _load("candidate_envelope.json")
    out = link(source, [candidate])
    write_into_envelope(source, out)

    expected = _load("source_with_relationship.json")
    assert _strip_volatile(source) == _strip_volatile(expected)


def test_apply_relationship_decision_on_examples_matches_stored() -> None:
    source = _load("source_envelope.json")
    candidate = _load("candidate_envelope.json")
    out = link(source, [candidate])
    write_into_envelope(source, out)
    rel_id = out.candidates[0].relationship_id
    apply_relationship_decision(source, rel_id, "confirmed", "human_review", rationale="vendor verified")

    expected = _load("source_confirmed.json")
    assert _strip_volatile(source) == _strip_volatile(expected)


def test_linker_output_pins_status_and_discovered_by() -> None:
    out_dict = _load("linker_output.json")
    assert out_dict["candidates"], "expected at least one candidate"
    for c in out_dict["candidates"]:
        assert c["status"] == "suggested"
        assert c["discovered_by"] == "gallodoc-linker/3.0.0"


def test_confirmed_envelope_preserves_discovered_by() -> None:
    """The audit trail: confirmed entry must still show discovered_by = linker."""
    env = _load("source_confirmed.json")
    rels = env["relationships"]["relationships"]
    assert rels, "expected at least one relationship"
    target = rels[0]
    assert target["status"] == "confirmed"
    assert target["discovered_by"] == "gallodoc-linker/3.0.0"
    decisions = env["relationships"]["relationship_decisions"]
    assert decisions, "expected a decision record"
    assert decisions[0]["verdict"] == "confirmed"
    assert decisions[0]["decided_by"] == "human_review"


def test_suggested_envelope_passes_validate() -> None:
    """The merged-but-suggested envelope passes v3 validation
    (specifically the linker rule pinning to status=suggested)."""
    env = _load("source_with_relationship.json")
    result = validate_envelope(env)
    assert result.valid, f"errors: {[(i.path, i.message) for i in result.errors()]}"


def test_confirmed_envelope_validates() -> None:
    """The confirmed envelope validates under the Decision 3 lifecycle rule.

    `apply_relationship_decision` preserves `discovered_by` (audit trail)
    and appends a record to `relationship_decisions[]`. The validator now
    allows `status: "confirmed"` on a linker-discovered relationship as long
    as a matching `relationship_decisions[]` entry exists for the same
    `relationship_id` — closing the earlier Decision-3-vs-validator gap.
    """
    env = _load("source_confirmed.json")
    result = validate_envelope(env)
    linker_issues = [
        i for i in result.errors()
        if i.path.endswith(".status") and "linker" in i.message
    ]
    assert not linker_issues, (
        f"confirmed envelope with a matching decision record should validate, "
        f"got linker issues: {[(i.path, i.message) for i in linker_issues]}"
    )
    assert result.valid, f"errors: {[(i.path, i.message) for i in result.errors()]}"
