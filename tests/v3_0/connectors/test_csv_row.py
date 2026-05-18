"""Tests for the csv_row connector."""

from __future__ import annotations

from pathlib import Path

import pytest

from gallodoc.connectors import CsvRowConnector
from gallodoc.validation import validate_envelope


def _write_csv(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "input.csv"
    p.write_text(body, encoding="utf-8")
    return p


def test_read_yields_one_record_per_row(tmp_path: Path):
    """The connector yields exactly one record per data row."""
    p = _write_csv(
        tmp_path,
        "id,title,note\nrow-a,A,first\nrow-b,B,second\nrow-c,C,third\n",
    )
    c = CsvRowConnector()
    records = list(c.read(p))
    assert len(records) == 3
    assert records[0].payload["title"] == "A"
    assert records[2].payload["title"] == "C"


def test_read_record_id_includes_filename_and_row_number(tmp_path: Path):
    """`record_id` is `filename:row:N` (1-indexed data rows)."""
    p = _write_csv(tmp_path, "id,title\nx,first\ny,second\n")
    c = CsvRowConnector()
    records = list(c.read(p))
    assert records[0].record_id == "input.csv:row:1"
    assert records[1].record_id == "input.csv:row:2"


def test_to_envelope_passes_v3_validator(tmp_path: Path):
    """Each produced envelope passes `validate_envelope`."""
    p = _write_csv(tmp_path, "id,title\nrow-1,Title 1\nrow-2,Title 2\n")
    c = CsvRowConnector()
    envelopes = list(c.to_envelopes(p))
    assert len(envelopes) == 2
    for env in envelopes:
        result = validate_envelope(env)
        assert result.valid, [i.message for i in result.issues if i.severity == "error"]


def test_column_map_routes_columns_correctly(tmp_path: Path):
    """Default column map routes id/title to identity.*."""
    p = _write_csv(tmp_path, "id,title\nABC,My Title\n")
    c = CsvRowConnector()
    env = list(c.to_envelopes(p))[0]
    assert env["identity"]["gallodoc_id"] == "ABC"
    assert env["identity"]["title"] == "My Title"


def test_custom_column_map_overrides_default(tmp_path: Path):
    """A custom column map replaces the default."""
    p = _write_csv(tmp_path, "subject,score\nUreaCycle,98\n")
    c = CsvRowConnector(column_map={"subject": "identity.title"})
    env = list(c.to_envelopes(p))[0]
    assert env["identity"]["title"] == "UreaCycle"
    # `score` was unmapped → lands in extensions.
    bucket = env["extensions"]["connector_input"]["csv_row"]["row"]
    assert bucket["score"] == "98"


def test_source_lineage_populated_per_row(tmp_path: Path):
    """`source.connector_lineage` populates with `csv_row` slug + per-row receipts."""
    p = _write_csv(tmp_path, "id,title\nq,X\nr,Y\n")
    c = CsvRowConnector()
    envelopes = list(c.to_envelopes(p))
    for env in envelopes:
        lin = env["source"]["connector_lineage"]
        assert lin["sync_runs"][0]["connector_slug"] == "csv_row"
        assert lin["record_receipts"][0]["source_record_id_hash"].startswith("sha256:")


def test_missing_file_raises_file_not_found(tmp_path: Path):
    """A missing source path raises `FileNotFoundError`."""
    c = CsvRowConnector()
    with pytest.raises(FileNotFoundError):
        list(c.read(tmp_path / "does_not_exist.csv"))
