"""Tests for the salesforce_account_stub connector."""

from __future__ import annotations

import json
import re

import pytest

from gallodoc.connectors import SalesforceAccountStubConnector
from gallodoc.validation import validate_envelope


def _fixture_account() -> dict:
    return {
        "account_id": "001-EX-0001",
        "name": "Acme Health",
        "type": "Customer",
        "industry": "Healthcare",
        "owner_email": "rep@example.com",
    }


def test_to_envelope_passes_v3_validator():
    """The produced envelope passes `validate_envelope`."""
    c = SalesforceAccountStubConnector()
    env = list(c.to_envelopes(_fixture_account()))[0]
    result = validate_envelope(env)
    assert result.valid, [i.message for i in result.issues if i.severity == "error"]


def test_source_system_is_salesforce():
    """`source.source_system == 'salesforce'`."""
    c = SalesforceAccountStubConnector()
    env = list(c.to_envelopes(_fixture_account()))[0]
    assert env["source"]["source_system"] == "salesforce"


def test_source_kind_is_account():
    """`source.source_kind == 'account'`."""
    c = SalesforceAccountStubConnector()
    env = list(c.to_envelopes(_fixture_account()))[0]
    assert env["source"]["source_kind"] == "account"


def test_identity_document_type_is_account_record():
    """`identity.document_type == 'account_record'`."""
    c = SalesforceAccountStubConnector()
    env = list(c.to_envelopes(_fixture_account()))[0]
    assert env["identity"]["document_type"] == "account_record"
    assert env["identity"]["title"] == "Acme Health"


def test_gallounits_units_non_empty():
    """`gallounits.units` has at least one entry."""
    c = SalesforceAccountStubConnector()
    env = list(c.to_envelopes(_fixture_account()))[0]
    units = env["gallounits"]["units"]
    assert len(units) >= 1
    # Each unit has deterministic unit_id + text_hash.
    for u in units:
        assert u["unit_id"].startswith("sha256:")
        assert u["text_hash"].startswith("sha256:")
        assert u["unit_type"] == "entity"


def test_no_real_email_domains_in_output():
    """The validator's email rule rejects non-example.com domains —
    using only `example.com` in the input means no banned email
    survives in the output."""
    c = SalesforceAccountStubConnector()
    env = list(c.to_envelopes(_fixture_account()))[0]
    blob = json.dumps(env)
    disallowed = re.compile(
        r"\b[\w.+-]+@(?!example\.com\b|halobridge\.ai\b)[\w.-]+\.[a-z]{2,}\b",
        re.IGNORECASE,
    )
    assert not disallowed.search(blob)


def test_list_input_yields_multiple_envelopes():
    """A list of two accounts yields two envelopes."""
    c = SalesforceAccountStubConnector()
    envelopes = list(
        c.to_envelopes(
            [
                _fixture_account(),
                {
                    "account_id": "001-EX-0002",
                    "name": "Beta Clinic",
                    "type": "Prospect",
                    "industry": "Healthcare",
                },
            ]
        )
    )
    assert len(envelopes) == 2
    assert envelopes[0]["identity"]["title"] == "Acme Health"
    assert envelopes[1]["identity"]["title"] == "Beta Clinic"


def test_lineage_populated():
    """`source.connector_lineage.sync_runs[0].connector_slug` matches."""
    c = SalesforceAccountStubConnector()
    env = list(c.to_envelopes(_fixture_account()))[0]
    lin = env["source"]["connector_lineage"]
    assert lin["sync_runs"][0]["connector_slug"] == "salesforce_account_stub"
    assert lin["record_receipts"][0]["source_record_id_hash"].startswith("sha256:")


def test_extensions_carry_input():
    """`extensions.connector_input.salesforce_account_stub` carries the input."""
    c = SalesforceAccountStubConnector()
    env = list(c.to_envelopes(_fixture_account()))[0]
    bucket = env["extensions"]["connector_input"]["salesforce_account_stub"]
    assert bucket["account_id"] == "001-EX-0001"
    assert bucket["name"] == "Acme Health"
