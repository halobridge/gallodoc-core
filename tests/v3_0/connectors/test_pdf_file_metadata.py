"""Tests for the pdf_file_metadata connector."""

from __future__ import annotations

from pathlib import Path

import pytest

from gallodoc.connectors import PdfFileMetadataConnector
from gallodoc.connectors import pdf_file_metadata as pdf_mod
from gallodoc.validation import validate_envelope


# A tiny valid PDF — minimum acceptable header + EOF marker. The
# connector doesn't parse contents (pypdf is optional), so the byte
# body just needs to be a real file with non-zero size.
_TINY_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<<>>endobj\n"
    b"xref\n0 1\n0000000000 65535 f \n"
    b"trailer<<>>\nstartxref\n0\n%%EOF\n"
)


def _write_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "sample.pdf"
    p.write_bytes(_TINY_PDF)
    return p


def test_read_returns_one_record(tmp_path: Path):
    """One file → one record."""
    p = _write_pdf(tmp_path)
    c = PdfFileMetadataConnector()
    records = list(c.read(p))
    assert len(records) == 1


def test_read_payload_has_expected_metadata_keys(tmp_path: Path):
    """Payload carries file_size_bytes, mtime_iso, page_count, file_path_hash."""
    p = _write_pdf(tmp_path)
    c = PdfFileMetadataConnector()
    record = list(c.read(p))[0]
    payload = record.payload
    assert payload["file_size_bytes"] == len(_TINY_PDF)
    assert payload["mtime_iso"].endswith("Z")
    assert payload["file_path_hash"].startswith("sha256:")
    # page_count is present (value may be int or None depending on pypdf).
    assert "page_count" in payload


def test_to_envelope_passes_v3_validator(tmp_path: Path):
    """The produced envelope passes `validate_envelope`."""
    p = _write_pdf(tmp_path)
    c = PdfFileMetadataConnector()
    env = list(c.to_envelopes(p))[0]
    result = validate_envelope(env)
    assert result.valid, [i.message for i in result.issues if i.severity == "error"]


def test_envelope_mime_type_is_application_pdf(tmp_path: Path):
    """The envelope declares `mime_type: 'application/pdf'`."""
    p = _write_pdf(tmp_path)
    c = PdfFileMetadataConnector()
    env = list(c.to_envelopes(p))[0]
    assert env["identity"]["mime_type"] == "application/pdf"
    assert env["identity"]["document_type"] == "pdf_file"


def test_page_count_none_when_pypdf_missing(tmp_path: Path, monkeypatch):
    """If pypdf can't import, `page_count` is `None`."""
    # Force the import inside _read_page_count to fail by stubbing the
    # helper to behave as if pypdf were missing.
    monkeypatch.setattr(pdf_mod, "_read_page_count", lambda _path: None)
    p = _write_pdf(tmp_path)
    c = PdfFileMetadataConnector()
    record = list(c.read(p))[0]
    assert record.payload["page_count"] is None


def test_missing_file_raises_file_not_found(tmp_path: Path):
    """A non-existent path raises FileNotFoundError."""
    c = PdfFileMetadataConnector()
    with pytest.raises(FileNotFoundError):
        list(c.read(tmp_path / "missing.pdf"))


def test_source_connector_lineage_populated(tmp_path: Path):
    """`source.connector_lineage.sync_runs[0]` is populated."""
    p = _write_pdf(tmp_path)
    c = PdfFileMetadataConnector()
    env = list(c.to_envelopes(p))[0]
    lineage = env["source"]["connector_lineage"]
    assert lineage["sync_runs"][0]["connector_slug"] == "pdf_file_metadata"
    assert lineage["sync_runs"][0]["status"] == "completed"
