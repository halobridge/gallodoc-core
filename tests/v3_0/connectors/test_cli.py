"""CLI integration tests for `gallodoc connector convert`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.cli.main import main as cli_main
from gallodoc.connectors import CONNECTORS
from gallodoc.connectors.cli import cli_connector_convert
from gallodoc.validation import validate_envelope


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_has_five_starter_connectors():
    """The CONNECTORS registry contains the five starter slugs."""
    expected = {
        "csv_row",
        "generic_json",
        "invoice_stub",
        "pdf_file_metadata",
        "salesforce_account_stub",
    }
    assert set(CONNECTORS) == expected


# ---------------------------------------------------------------------------
# generic_json
# ---------------------------------------------------------------------------


def test_cli_generic_json_writes_valid_envelope(tmp_path: Path):
    inp = tmp_path / "input.json"
    inp.write_text(
        json.dumps({"id": "doc-001", "title": "Hello", "document_type": "note"}),
        encoding="utf-8",
    )
    out = tmp_path / "out.gdoc.json"
    rc = cli_connector_convert("generic_json", str(inp), str(out))
    assert rc == 0
    assert out.exists()
    env = json.loads(out.read_text(encoding="utf-8"))
    assert validate_envelope(env).valid


# ---------------------------------------------------------------------------
# csv_row
# ---------------------------------------------------------------------------


def test_cli_csv_row_writes_array_envelope(tmp_path: Path):
    inp = tmp_path / "input.csv"
    inp.write_text("id,title\nrow-1,Title 1\nrow-2,Title 2\n", encoding="utf-8")
    out = tmp_path / "out.gdoc.json"
    rc = cli_connector_convert("csv_row", str(inp), str(out))
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    # Multiple records → JSON array.
    assert isinstance(data, list)
    assert len(data) == 2
    for env in data:
        assert validate_envelope(env).valid


# ---------------------------------------------------------------------------
# pdf_file_metadata
# ---------------------------------------------------------------------------


def test_cli_pdf_file_metadata_writes_valid_envelope(tmp_path: Path):
    inp = tmp_path / "sample.pdf"
    inp.write_bytes(b"%PDF-1.4\n%%EOF\n")
    out = tmp_path / "out.gdoc.json"
    rc = cli_connector_convert("pdf_file_metadata", str(inp), str(out))
    assert rc == 0
    env = json.loads(out.read_text(encoding="utf-8"))
    assert validate_envelope(env).valid
    assert env["identity"]["mime_type"] == "application/pdf"


# ---------------------------------------------------------------------------
# salesforce_account_stub
# ---------------------------------------------------------------------------


def test_cli_salesforce_stub_writes_valid_envelope(tmp_path: Path):
    inp = tmp_path / "account.json"
    inp.write_text(
        json.dumps(
            {
                "account_id": "001-EX-0001",
                "name": "Acme Health",
                "type": "Customer",
                "industry": "Healthcare",
                "owner_email": "rep@example.com",
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.gdoc.json"
    rc = cli_connector_convert("salesforce_account_stub", str(inp), str(out))
    assert rc == 0
    env = json.loads(out.read_text(encoding="utf-8"))
    assert validate_envelope(env).valid
    assert env["source"]["source_system"] == "salesforce"


# ---------------------------------------------------------------------------
# invoice_stub
# ---------------------------------------------------------------------------


def test_cli_invoice_stub_writes_valid_envelope(tmp_path: Path):
    inp = tmp_path / "invoice.json"
    inp.write_text(
        json.dumps(
            {
                "invoice_id": "INV-001",
                "vendor_name": "Vendor LLC",
                "total_amount": 100.0,
                "currency": "USD",
                "due_date": "2026-06-01",
                "line_items": [
                    {"description": "Widget", "quantity": 1, "unit_price": 100.0, "amount": 100.0},
                ],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.gdoc.json"
    rc = cli_connector_convert("invoice_stub", str(inp), str(out))
    assert rc == 0
    env = json.loads(out.read_text(encoding="utf-8"))
    assert validate_envelope(env).valid
    assert env["identity"]["document_type"] == "invoice"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_cli_bad_slug_returns_nonzero(tmp_path: Path, capsys):
    """A bad connector slug returns non-zero exit and an error on stderr."""
    inp = tmp_path / "input.json"
    inp.write_text("{}", encoding="utf-8")
    out = tmp_path / "out.gdoc.json"
    rc = cli_connector_convert("does_not_exist", str(inp), str(out))
    assert rc != 0
    captured = capsys.readouterr()
    assert "unknown connector slug" in captured.err
    # Must NOT have produced the output file.
    assert not out.exists()


def test_cli_missing_input_returns_nonzero(tmp_path: Path, capsys):
    """A missing input file returns non-zero exit."""
    out = tmp_path / "out.gdoc.json"
    rc = cli_connector_convert(
        "generic_json", str(tmp_path / "does_not_exist.json"), str(out)
    )
    assert rc != 0
    captured = capsys.readouterr()
    assert "input not found" in captured.err


# ---------------------------------------------------------------------------
# main entry-point smoke test
# ---------------------------------------------------------------------------


def test_main_dispatches_connector_convert(tmp_path: Path):
    """The top-level `gallodoc` parser routes `connector convert` correctly."""
    inp = tmp_path / "input.json"
    inp.write_text(
        json.dumps({"id": "doc-via-main", "title": "Via main"}),
        encoding="utf-8",
    )
    out = tmp_path / "out.gdoc.json"
    rc = cli_main(
        [
            "connector",
            "convert",
            "--connector",
            "generic_json",
            "--input",
            str(inp),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    env = json.loads(out.read_text(encoding="utf-8"))
    assert validate_envelope(env).valid
