"""Tests for the rule-based unit classifier."""

from __future__ import annotations

from gallodoc.units.classifier import UnitClassifier, classify_unit


def test_classifier_reports_confidence_and_type():
    out = classify_unit("Net 30 payment terms apply.")
    assert out["unit_type"] == "payment_terms"
    assert out["semantic_role"] == "payment_terms"
    assert 0.0 <= out["confidence"] <= 1.0


def test_classifier_handles_signatures():
    out = classify_unit("Signature: ___________________________")
    assert out["unit_type"] == "signature_block"


def test_classifier_handles_headings():
    out = classify_unit("MASTER SERVICES AGREEMENT")
    assert out["unit_type"] == "heading"


def test_classifier_handles_table_rows():
    out = classify_unit("Item | Qty | Amount")
    assert out["unit_type"] == "table_row"


def test_classifier_handles_line_items():
    out = classify_unit("- One unit of synthetic widget A")
    assert out["unit_type"] == "line_item"


def test_classifier_handles_amounts_and_dates():
    assert classify_unit("Total $1,234.56")["unit_type"] == "amount_block"
    assert classify_unit("2026-04-30")["unit_type"] == "date_block"


def test_classifier_handles_legal_clause():
    out = classify_unit("The provider shall deliver the work product within 14 days.")
    assert out["unit_type"] == "clause"


def test_classifier_falls_back_to_paragraph():
    out = classify_unit("This is just a normal sentence with no obvious structure.")
    assert out["unit_type"] == "paragraph"


def test_no_optional_backend_required():
    """Default classifier must work without optional dependencies."""
    cls = UnitClassifier(use_optional_backend=False)
    assert cls.classify("Net 30 payment terms apply.")["unit_type"] == "payment_terms"


def test_classifier_returns_unknown_for_empty_input():
    out = classify_unit("")
    assert out["unit_type"] == "unknown"
    assert out["confidence"] == 0.0
