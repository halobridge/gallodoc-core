"""Tests for the basic artifact extractor."""

from __future__ import annotations

from gallodoc.artifacts import ARTIFACT_TYPES, extract_basic_artifacts
from gallodoc.units import build_gallounits_block


SAMPLE = """\
INVOICE 2026-001

Invoice Date: 2026-04-30
Due Date: 2026-05-30

Bill To: synthetic@example.com
Phone: +1 415 555 0199
Reference: PO-7788-C

- Synthetic widget A — $1,234.56
- Synthetic widget B — $42.00

Net 30 payment terms apply.

Signature: ______________________
"""


def test_extract_returns_typed_artifacts():
    units = build_gallounits_block(SAMPLE)["units"]
    artifacts = extract_basic_artifacts(units)
    types = {a["artifact_type"] for a in artifacts}
    # We don't insist on every type, but at least these should fire.
    assert {"date", "amount", "email", "phone", "reference_id", "payment_terms", "line_item_candidate"} <= types
    for a in artifacts:
        assert a["artifact_type"] in ARTIFACT_TYPES
        assert a["method"] == "regex_v1"
        assert a["source_unit_id"]
        assert "needs_review" in a
        assert 0.0 <= a["confidence"] <= 1.0


def test_extract_empty_units_returns_empty():
    assert extract_basic_artifacts([]) == []


def test_extract_marks_iso_dates_with_high_confidence():
    units = build_gallounits_block("Issued 2026-04-30.")["units"]
    artifacts = extract_basic_artifacts(units)
    iso_dates = [a for a in artifacts if a["artifact_type"] == "date" and a["fields"].get("format") == "iso"]
    assert iso_dates
    assert iso_dates[0]["confidence"] >= 0.8


def test_extract_marks_phone_needs_review():
    units = build_gallounits_block("Phone: +1 415 555 0199")["units"]
    arts = [a for a in extract_basic_artifacts(units) if a["artifact_type"] == "phone"]
    assert arts
    assert all(a["needs_review"] for a in arts)
