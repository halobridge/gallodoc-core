"""Verify the committed examples under ``examples/v3_0/connectors/``.

For each (input, output) pair:
- The committed output validates as v3.
- Running the connector on the committed input, then stabilizing
  volatile fields (timestamps, sync_run_ids, mtime, file size),
  reproduces the committed output structurally.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gallodoc.connectors import (
    CONNECTORS,
    CsvRowConnector,
    GenericJsonConnector,
    InvoiceStubConnector,
    PdfFileMetadataConnector,
    SalesforceAccountStubConnector,
)
from gallodoc.validation import validate_envelope


EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples" / "v3_0" / "connectors"


PLACEHOLDER_TS = "2026-05-16T00:00:00Z"
PLACEHOLDER_PATH_HASH = (
    "sha256:0000000000000000000000000000000000000000000000000000000000000000"
)


def _placeholder_sync_id(slug: str) -> str:
    return f"sync-{slug}-EXAMPLE0001"


def _stabilize(envelope: dict, slug: str, *, pdf_size: int | None = None) -> dict:
    """Replace volatile fields with deterministic placeholders.

    Mirrors the stabilizer used to generate the committed examples.
    Volatile fields = timestamps, sync_run_ids, path-derived hashes
    (which vary with the filesystem absolute path), and file metadata
    (mtime, size).
    """
    env = copy.deepcopy(envelope)
    lin = env.get("source", {}).get("connector_lineage", {})
    for sr in lin.get("sync_runs", []):
        sr["started_at"] = PLACEHOLDER_TS
        sr["completed_at"] = PLACEHOLDER_TS
        sr["sync_run_id"] = _placeholder_sync_id(slug)
        if sr.get("source_ref_hash") is not None and sr["source_ref_hash"] != "":
            sr["source_ref_hash"] = PLACEHOLDER_PATH_HASH
    for rr in lin.get("record_receipts", []):
        rr["sync_run_id"] = _placeholder_sync_id(slug)
        rr["receipt_id"] = "rcpt-" + _placeholder_sync_id(slug)
        # For path-derived connectors (pdf_file_metadata), these fields embed
        # the filesystem absolute path and would otherwise differ per checkout
        # location. Normalize to placeholders so the example diffs cleanly.
        if slug == "pdf_file_metadata":
            for k in ("gallodoc_ref",):
                if k in rr and isinstance(rr[k], str):
                    rr[k] = "pdf-file:" + PLACEHOLDER_PATH_HASH
            for k in ("record_hash", "source_record_id_hash"):
                if k in rr and isinstance(rr[k], str):
                    rr[k] = PLACEHOLDER_PATH_HASH
    env.setdefault("source", {})["sync_run_id"] = _placeholder_sync_id(slug)
    if "created_at" in env.get("identity", {}):
        env["identity"]["created_at"] = PLACEHOLDER_TS
    # PDF-connector gallodoc_id is derived from the file's absolute path.
    if slug == "pdf_file_metadata":
        identity = env.get("identity", {})
        gid = identity.get("gallodoc_id")
        if isinstance(gid, str) and gid.startswith("pdf-file:sha256:"):
            identity["gallodoc_id"] = "pdf-file:" + PLACEHOLDER_PATH_HASH
    for cl in env.get("truth_ledger", {}).get("claims", []):
        if "created_at" in cl:
            cl["created_at"] = PLACEHOLDER_TS
    bucket = env.get("extensions", {}).get("connector_input", {}).get(
        "pdf_file_metadata"
    )
    if isinstance(bucket, dict):
        bucket["mtime_iso"] = PLACEHOLDER_TS
        if pdf_size is not None:
            bucket["file_size_bytes"] = pdf_size
        if "file_path_hash" in bucket:
            bucket["file_path_hash"] = PLACEHOLDER_PATH_HASH
    return env


# ---------------------------------------------------------------------------
# Validate every committed output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "generic_json_output.gdoc.json",
        "csv_row_output.gdoc.json",
        "pdf_file_metadata_output.gdoc.json",
        "salesforce_account_stub_output.gdoc.json",
        "invoice_stub_output.gdoc.json",
    ],
)
def test_committed_output_validates(filename):
    """Each committed `*_output.gdoc.json` passes `validate_envelope`."""
    path = EXAMPLES_DIR / filename
    env = json.loads(path.read_text(encoding="utf-8"))
    result = validate_envelope(env)
    assert result.valid, [i.message for i in result.issues if i.severity == "error"]


# ---------------------------------------------------------------------------
# Re-run each connector and compare structural equality
# ---------------------------------------------------------------------------


def _expected(filename: str) -> dict:
    return json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))


def test_generic_json_example_reproduces():
    inp = json.loads(
        (EXAMPLES_DIR / "generic_json_input.json").read_text(encoding="utf-8")
    )
    env = list(GenericJsonConnector().to_envelopes(inp))[0]
    stabilized = _stabilize(env, "generic_json")
    assert stabilized == _expected("generic_json_output.gdoc.json")


def test_csv_row_example_reproduces():
    envs = list(
        CsvRowConnector().to_envelopes(EXAMPLES_DIR / "csv_row_input.csv")
    )
    # First row only — matches what the committed output captures.
    stabilized = _stabilize(envs[0], "csv_row")
    assert stabilized == _expected("csv_row_output.gdoc.json")


def test_pdf_file_metadata_example_reproduces():
    pdf_path = EXAMPLES_DIR / "pdf_file_metadata_input.pdf"
    pdf_size = pdf_path.stat().st_size
    env = list(PdfFileMetadataConnector().to_envelopes(pdf_path))[0]
    stabilized = _stabilize(env, "pdf_file_metadata", pdf_size=pdf_size)
    # The committed example fixed pdf_size at 86; assert ours matches
    # the committed value (the input file is checked in, so it must
    # stay the same size).
    assert pdf_size == 86
    assert stabilized == _expected("pdf_file_metadata_output.gdoc.json")


def test_salesforce_account_stub_example_reproduces():
    inp = json.loads(
        (EXAMPLES_DIR / "salesforce_account_stub_input.json").read_text(
            encoding="utf-8"
        )
    )
    env = list(SalesforceAccountStubConnector().to_envelopes(inp))[0]
    stabilized = _stabilize(env, "salesforce_account_stub")
    assert stabilized == _expected("salesforce_account_stub_output.gdoc.json")


def test_invoice_stub_example_reproduces():
    inp = json.loads(
        (EXAMPLES_DIR / "invoice_stub_input.json").read_text(encoding="utf-8")
    )
    env = list(InvoiceStubConnector().to_envelopes(inp))[0]
    stabilized = _stabilize(env, "invoice_stub")
    assert stabilized == _expected("invoice_stub_output.gdoc.json")


# ---------------------------------------------------------------------------
# Sanity check: every starter slug has an example pair on disk
# ---------------------------------------------------------------------------


def test_every_registered_connector_has_example_pair():
    """Each slug in CONNECTORS has an input and an output file present."""
    for slug in CONNECTORS:
        # Inputs use whichever extension is most natural per connector.
        candidates = [
            EXAMPLES_DIR / f"{slug}_input.json",
            EXAMPLES_DIR / f"{slug}_input.csv",
            EXAMPLES_DIR / f"{slug}_input.pdf",
        ]
        assert any(c.exists() for c in candidates), (
            f"no input file found for connector {slug}"
        )
        out = EXAMPLES_DIR / f"{slug}_output.gdoc.json"
        assert out.exists(), f"missing output for {slug}"
