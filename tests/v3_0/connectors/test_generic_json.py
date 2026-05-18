"""Tests for the generic_json connector."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest

from gallodoc.connectors import GenericJsonConnector
from gallodoc.validation import validate_envelope


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


def test_read_accepts_dict():
    """A single dict yields exactly one record."""
    c = GenericJsonConnector()
    records = list(c.read({"id": "doc-001", "title": "Hello"}))
    assert len(records) == 1
    assert records[0].payload["id"] == "doc-001"


def test_read_accepts_list_of_dicts():
    """A list yields one record per dict."""
    c = GenericJsonConnector()
    records = list(
        c.read([{"id": "a", "title": "A"}, {"id": "b", "title": "B"}, {"id": "c"}])
    )
    assert len(records) == 3
    assert [r.record_id for r in records] == ["a", "b", "c"]


def test_read_accepts_json_string():
    """A JSON string is parsed before being routed."""
    c = GenericJsonConnector()
    s = json.dumps({"id": "doc-007", "title": "From string"})
    records = list(c.read(s))
    assert len(records) == 1
    assert records[0].payload["id"] == "doc-007"


def test_read_accepts_path(tmp_path: Path):
    """A path on disk is read + parsed."""
    p = tmp_path / "input.json"
    p.write_text(json.dumps({"id": "doc-file", "title": "From file"}), encoding="utf-8")
    c = GenericJsonConnector()
    records = list(c.read(p))
    assert len(records) == 1
    assert records[0].payload["id"] == "doc-file"
    assert records[0].raw_source_ref == str(p)


# ---------------------------------------------------------------------------
# to_envelope — validity
# ---------------------------------------------------------------------------


def test_to_envelope_passes_v3_validator():
    """The produced envelope passes `validate_envelope`."""
    c = GenericJsonConnector()
    env = next(iter(c.to_envelopes({"id": "doc-100", "title": "Hello", "document_type": "note"})))
    result = validate_envelope(env)
    assert result.valid, [i.message for i in result.issues if i.severity == "error"]


def test_field_map_routes_keys_to_envelope_paths():
    """The default field map routes id/title/document_type correctly."""
    c = GenericJsonConnector()
    env = next(iter(c.to_envelopes({"id": "doc-200", "title": "Title", "document_type": "memo"})))
    assert env["identity"]["gallodoc_id"] == "doc-200"
    assert env["identity"]["title"] == "Title"
    assert env["identity"]["document_type"] == "memo"


def test_custom_field_map_overrides_default():
    """A custom field map replaces the default routing."""
    c = GenericJsonConnector(field_map={"label": "identity.title"})
    env = next(iter(c.to_envelopes({"label": "Custom Title"})))
    assert env["identity"]["title"] == "Custom Title"


def test_unmapped_keys_land_under_extensions():
    """Keys not in the field map go under
    `extensions.connector_input.generic_json`."""
    c = GenericJsonConnector()
    env = next(
        iter(
            c.to_envelopes(
                {"id": "doc-300", "weird_key": "stays", "another": 42}
            )
        )
    )
    bucket = env["extensions"]["connector_input"]["generic_json"]
    assert bucket["weird_key"] == "stays"
    assert bucket["another"] == 42
    # mapped keys do NOT appear in the bucket.
    assert "id" not in bucket


def test_source_connector_slug_set():
    """`source.connector_slug` is the connector's slug."""
    c = GenericJsonConnector()
    env = next(iter(c.to_envelopes({"id": "doc-400"})))
    assert env["source"]["connector_slug"] == "generic_json"


def test_source_connector_lineage_populated():
    """`source.connector_lineage.sync_runs[0]` has the required fields."""
    c = GenericJsonConnector()
    env = next(iter(c.to_envelopes({"id": "doc-500"})))
    lineage = env["source"]["connector_lineage"]
    assert lineage["schema_version"] == "gallodoc.connector_lineage.v2.0"
    assert len(lineage["sync_runs"]) == 1
    sr = lineage["sync_runs"][0]
    assert sr["connector_slug"] == "generic_json"
    assert sr["status"] == "completed"
    assert sr["started_at"].endswith("Z")
    # record_receipts populated.
    assert len(lineage["record_receipts"]) == 1
    assert lineage["record_receipts"][0]["source_record_id_hash"].startswith("sha256:")


def test_no_phi_or_real_email_in_output():
    """Input with only example.com data → no banned email patterns in output."""
    c = GenericJsonConnector()
    env = next(
        iter(
            c.to_envelopes(
                {
                    "id": "doc-600",
                    "title": "From rep@example.com",
                    "document_type": "note",
                }
            )
        )
    )
    blob = json.dumps(env)
    # The v3 validator's _EMAIL_DISALLOWED regex.
    disallowed = re.compile(
        r"\b[\w.+-]+@(?!example\.com\b|halobridge\.ai\b)[\w.-]+\.[a-z]{2,}\b",
        re.IGNORECASE,
    )
    assert not disallowed.search(blob)


def test_forbidden_keys_in_input_are_stripped_from_extensions():
    """A payload containing `api_key` is scrubbed by `project_to_open_core`."""
    c = GenericJsonConnector()
    env = next(
        iter(
            c.to_envelopes(
                {"id": "doc-700", "api_key": "should-not-survive", "title": "Test"}
            )
        )
    )
    blob = json.dumps(env)
    assert "should-not-survive" not in blob
