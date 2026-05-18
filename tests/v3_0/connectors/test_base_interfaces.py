"""Tests for the connector SDK base interfaces."""

from __future__ import annotations

import re

import pytest

from gallodoc.connectors import (
    ConnectorRecord,
    ConnectorRunReceipt,
    GalloDocConnector,
)
from gallodoc.connectors.base import hash_path, hash_str, now_iso


# ---------------------------------------------------------------------------
# Imports / surface
# ---------------------------------------------------------------------------


def test_public_surface_is_importable():
    """The three documented types import from `gallodoc.connectors`."""
    assert ConnectorRecord.__name__ == "ConnectorRecord"
    assert ConnectorRunReceipt.__name__ == "ConnectorRunReceipt"
    assert GalloDocConnector.__name__ == "GalloDocConnector"


# ---------------------------------------------------------------------------
# ConnectorRecord
# ---------------------------------------------------------------------------


def test_connector_record_id_hash_is_deterministic():
    """Same `record_id` always produces the same `sha256:` hash."""
    a = ConnectorRecord(record_id="invoice-001", payload={})
    b = ConnectorRecord(record_id="invoice-001", payload={"different": "payload"})
    assert a.record_id_hash == b.record_id_hash
    assert a.record_id_hash.startswith("sha256:")
    # SHA-256 hex is 64 chars + the `sha256:` prefix.
    assert len(a.record_id_hash) == len("sha256:") + 64


def test_connector_record_id_hash_changes_with_record_id():
    """Different `record_id` produces a different hash."""
    a = ConnectorRecord(record_id="invoice-001", payload={})
    b = ConnectorRecord(record_id="invoice-002", payload={})
    assert a.record_id_hash != b.record_id_hash


def test_connector_record_defaults():
    """`raw_source_ref` defaults to None, `record_metadata` to {}."""
    r = ConnectorRecord(record_id="x", payload={"k": "v"})
    assert r.raw_source_ref is None
    assert r.record_metadata == {}


# ---------------------------------------------------------------------------
# ConnectorRunReceipt
# ---------------------------------------------------------------------------


def test_run_receipt_to_dict_has_documented_keys():
    """`to_dict()` produces a dict with every documented key."""
    receipt = ConnectorRunReceipt(
        connector_slug="generic_json",
        connector_version="3.0.0",
        sync_run_id="run-001",
        started_at="2026-05-16T00:00:00Z",
        completed_at="2026-05-16T00:00:01Z",
        record_count=1,
        success_count=1,
        failed_count=0,
        source_ref_hash="sha256:abc",
        status="completed",
    )
    d = receipt.to_dict()
    expected_keys = {
        "sync_run_id",
        "connector_slug",
        "connector_version",
        "started_at",
        "completed_at",
        "record_count",
        "success_count",
        "failed_count",
        "source_ref_hash",
        "status",
    }
    assert set(d.keys()) == expected_keys
    assert d["sync_run_id"] == "run-001"
    assert d["connector_slug"] == "generic_json"
    assert d["status"] == "completed"


def test_run_receipt_default_status_is_completed():
    """`status` defaults to `completed` when omitted."""
    receipt = ConnectorRunReceipt(
        connector_slug="x",
        connector_version="3.0.0",
        sync_run_id="r",
        started_at="2026-05-16T00:00:00Z",
        completed_at="2026-05-16T00:00:01Z",
        record_count=0,
        success_count=0,
        failed_count=0,
    )
    assert receipt.status == "completed"
    assert receipt.source_ref_hash is None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_now_iso_returns_z_suffixed_iso_8601():
    """`now_iso` returns an ISO-8601 string ending in `Z`."""
    s = now_iso()
    assert isinstance(s, str)
    assert s.endswith("Z")
    # Shape: YYYY-MM-DDTHH:MM:SSZ
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", s)


def test_hash_str_is_sha256_prefixed():
    """`hash_str` returns `sha256:<64 hex chars>` deterministically."""
    h1 = hash_str("hello")
    h2 = hash_str("hello")
    h3 = hash_str("world")
    assert h1 == h2
    assert h1 != h3
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64


def test_hash_path_hashes_the_string_form():
    """`hash_path` hashes the stringified path."""
    h = hash_path("/tmp/example.json")
    assert h == hash_str("/tmp/example.json")


# ---------------------------------------------------------------------------
# GalloDocConnector abstract enforcement
# ---------------------------------------------------------------------------


def test_gallodoc_connector_is_abstract():
    """Cannot instantiate the abstract base class directly."""
    with pytest.raises(TypeError):
        GalloDocConnector()  # type: ignore[abstract]


def test_concrete_subclass_inherits_default_to_envelopes():
    """A minimal subclass gets `to_envelopes` for free."""

    class _Fake(GalloDocConnector):
        slug = "fake"
        version = "0.0.1"

        def read(self, source):
            yield ConnectorRecord(record_id="a", payload={"n": 1})
            yield ConnectorRecord(record_id="b", payload={"n": 2})

        def to_envelope(self, record):
            return {"schema_version": "gallodoc-core/v3", "n": record.payload["n"]}

    c = _Fake()
    out = list(c.to_envelopes(source=None))
    assert len(out) == 2
    assert out[0]["n"] == 1
    assert out[1]["n"] == 2
