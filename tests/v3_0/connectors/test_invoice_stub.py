"""Tests for the invoice_stub connector."""

from __future__ import annotations

import pytest

from gallodoc.connectors import InvoiceStubConnector
from gallodoc.validation import validate_envelope


def _fixture_invoice_3_lines() -> dict:
    return {
        "invoice_id": "INV-EX-0001",
        "vendor_name": "Example Vendor LLC",
        "total_amount": 1234.56,
        "currency": "USD",
        "due_date": "2026-06-01",
        "line_items": [
            {"description": "Widget A", "quantity": 2, "unit_price": 10.00, "amount": 20.00},
            {"description": "Widget B", "quantity": 3, "unit_price": 50.00, "amount": 150.00},
            {"description": "Service C", "quantity": 1, "unit_price": 1064.56, "amount": 1064.56},
        ],
    }


def test_to_envelope_passes_v3_validator():
    """The produced envelope passes `validate_envelope`."""
    c = InvoiceStubConnector()
    env = list(c.to_envelopes(_fixture_invoice_3_lines()))[0]
    result = validate_envelope(env)
    assert result.valid, [i.message for i in result.issues if i.severity == "error"]


def test_units_has_three_entries():
    """`gallounits.units` has exactly one entry per line item."""
    c = InvoiceStubConnector()
    env = list(c.to_envelopes(_fixture_invoice_3_lines()))[0]
    units = env["gallounits"]["units"]
    assert len(units) == 3


def test_each_unit_has_unique_unit_id_and_text_hash():
    """Each line-item unit carries a unique `unit_id` and non-empty `text_hash`."""
    c = InvoiceStubConnector()
    env = list(c.to_envelopes(_fixture_invoice_3_lines()))[0]
    units = env["gallounits"]["units"]
    unit_ids = [u["unit_id"] for u in units]
    text_hashes = [u["text_hash"] for u in units]
    # Unique unit_ids.
    assert len(set(unit_ids)) == 3
    for uid in unit_ids:
        assert uid.startswith("sha256:")
    # Non-empty text hashes.
    for th in text_hashes:
        assert th.startswith("sha256:")
        assert len(th) == len("sha256:") + 64


def test_truth_ledger_has_total_amount_claim():
    """`truth_ledger.claims` has at least one entry with `field_path == 'total_amount'`."""
    c = InvoiceStubConnector()
    env = list(c.to_envelopes(_fixture_invoice_3_lines()))[0]
    claims = env["truth_ledger"]["claims"]
    assert len(claims) >= 1
    total_claims = [cl for cl in claims if cl["field_path"] == "total_amount"]
    assert len(total_claims) == 1
    claim = total_claims[0]
    assert claim["claim_value_summary"] == "USD 1234.56"
    assert claim["status"] == "proposed"


def test_identity_document_type_is_invoice():
    """`identity.document_type == 'invoice'`."""
    c = InvoiceStubConnector()
    env = list(c.to_envelopes(_fixture_invoice_3_lines()))[0]
    assert env["identity"]["document_type"] == "invoice"
    assert "INV-EX-0001" in env["identity"]["title"]
    assert "Example Vendor LLC" in env["identity"]["title"]


def test_source_kind_is_invoice():
    """`source.source_kind == 'invoice'`."""
    c = InvoiceStubConnector()
    env = list(c.to_envelopes(_fixture_invoice_3_lines()))[0]
    assert env["source"]["source_kind"] == "invoice"
    assert env["source"]["source_system"] == "internal_invoice_system"


def test_evidence_refs_present():
    """`evidence.refs[]` references the source invoice."""
    c = InvoiceStubConnector()
    env = list(c.to_envelopes(_fixture_invoice_3_lines()))[0]
    refs = env["evidence"]["refs"]
    assert len(refs) >= 1
    assert refs[0]["source_ref"].startswith("invoice_id:")


def test_lineage_populated():
    """`source.connector_lineage` populated with invoice_stub slug."""
    c = InvoiceStubConnector()
    env = list(c.to_envelopes(_fixture_invoice_3_lines()))[0]
    lin = env["source"]["connector_lineage"]
    assert lin["sync_runs"][0]["connector_slug"] == "invoice_stub"


def test_empty_line_items_still_validates():
    """An invoice with no line items still produces a valid envelope."""
    c = InvoiceStubConnector()
    env = list(
        c.to_envelopes(
            {
                "invoice_id": "INV-EMPTY",
                "vendor_name": "Vendor",
                "total_amount": 0,
                "currency": "USD",
                "due_date": "2026-06-01",
                "line_items": [],
            }
        )
    )[0]
    result = validate_envelope(env)
    assert result.valid
    assert len(env["gallounits"]["units"]) == 0
