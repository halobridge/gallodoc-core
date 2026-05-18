# GalloDoc Core v3 — Open Connector SDK

**Status:** active — ships in v3.0.0 (Codex 03).
**Spec slug:** `gallodoc.connector_sdk.v3.0`
**Source code:** [`gallodoc/connectors/`](../../gallodoc/connectors/)
**Depends on:** [`gallodoc-core-v3-master-spec.md`](gallodoc-core-v3-master-spec.md),
[`gallodoc-core-v3-reference-projector.md`](gallodoc-core-v3-reference-projector.md),
[`gallodoc-connector-lineage-v2.md`](gallodoc-connector-lineage-v2.md).

## 1. Overview

A **GalloDoc Connector** is a small adapter that turns input from an
external system (a JSON document, a CSV row, a PDF file on disk, a
synthetic Salesforce account record, a synthetic invoice payload, …)
into a valid `gallodoc-core/v3` envelope. Connectors are the on-ramp:
"`pip install gallodoc && gallodoc connector convert --connector
generic_json --input my.json --out out.gdoc.json`" must produce a valid
v3 envelope in one step, with zero platform dependencies.

The SDK lives in `gallodoc.connectors`. It ships with five starter
connectors that cover the most common shapes a new user will hit on
day one. Every starter feeds its output through
[`project_to_open_core`](../../gallodoc/projection/projector.py) so the
output is guaranteed to be a valid v3 envelope — even if the connector
author makes a mistake.

### Why this lives in open-source

The "5-minute install" pitch only works if a new user can produce a
valid envelope from data they already have. Without a connector SDK,
every adopter has to re-implement the 18-required-section shape from
scratch, look up which keys are forbidden, and discover the
`source.connector_lineage` provenance rules. The SDK turns that into a
function call.

## 2. Interfaces

The SDK exposes three core types in `gallodoc.connectors.base`:

### `ConnectorRecord`

A single parsed record from a connector's source — stable shape across
all connectors:

```python
@dataclass
class ConnectorRecord:
    record_id: str                        # canonical id, free-form per connector
    payload: dict[str, Any]               # the parsed record body
    raw_source_ref: str | None = None     # opaque ref to the source (path:row, url, etc.)
    record_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def record_id_hash(self) -> str:
        """SHA-256 of record_id, prefixed `sha256:`. Used in lineage."""
```

### `GalloDocConnector`

The main interface. Each connector subclasses this and overrides four
attributes / methods:

```python
class GalloDocConnector(ABC):
    slug: str = ""             # stable connector slug, e.g. "invoice_stub"
    version: str = ""          # connector version, e.g. "3.0.0"

    @abstractmethod
    def read(self, source: Any) -> Iterable[ConnectorRecord]:
        """Parse input source into records."""

    @abstractmethod
    def to_envelope(self, record: ConnectorRecord) -> dict[str, Any]:
        """Turn one record into a v3 envelope. Must call
        gallodoc.projection.project_to_open_core internally so the
        result is guaranteed-valid v3."""

    def to_envelopes(self, source: Any) -> Iterator[dict[str, Any]]:
        """Compose read + to_envelope for the common case."""
        for record in self.read(source):
            yield self.to_envelope(record)
```

### `ConnectorRunReceipt`

Record of a connector run. Hashes and counts only — no raw record
content. Used as part of `source.connector_lineage.sync_runs[]`.

```python
@dataclass
class ConnectorRunReceipt:
    connector_slug: str
    connector_version: str
    sync_run_id: str
    started_at: str              # ISO-8601
    completed_at: str            # ISO-8601
    record_count: int
    success_count: int
    failed_count: int
    source_ref_hash: str | None = None    # SHA-256 of the source location
    status: str = "completed"             # completed | failed | partial
```

`ConnectorRunReceipt.to_dict()` produces a dict that fits the v2.0
`connector_lineage.sync_runs[]` shape (required fields:
`sync_run_id`, `connector_slug`, `started_at`, `status`).

## 3. Starter connectors

The SDK ships five starter connectors in `gallodoc.connectors`. Each
emits a v3 envelope via `project_to_open_core` so output is always
schema-valid. The connector registry lives in
`gallodoc.connectors.CONNECTORS` (a dict keyed by slug).

### `generic_json`

Accepts a JSON dict, a JSON string, a list of dicts, or a file
`Path`/`str`. Maps a configurable subset of input keys to envelope
fields via `field_map: dict[str, str]` (input-key → envelope dotted
path, e.g. `"id" -> "identity.gallodoc_id"`). Remaining keys land under
`extensions.connector_input.generic_json`.

The default field map is sensible for a hand-written JSON input:

```python
{
    "id":            "identity.gallodoc_id",
    "title":         "identity.title",
    "document_type": "identity.document_type",
}
```

Use this connector as the "convert any JSON to a baseline envelope"
on-ramp.

### `csv_row`

Accepts a CSV file path. Yields one `ConnectorRecord` per data row;
each row becomes a v3 envelope. Default column map:
`{"id": "identity.gallodoc_id", "title": "identity.title"}`.

`record_id` for each row is `f"{filename}:row:{rownum}"`, so the lineage
receipt is unique per row.

### `pdf_file_metadata`

Accepts a PDF file path. Reads file metadata only — size, mtime, and
(if `pypdf` is installed) page count. The envelope carries
`mime_type: "application/pdf"`, `document_type: "pdf_file"`, and the
file metadata under `extensions.connector_input.pdf_file_metadata`.

**This connector does NOT extract PDF text.** PDF text extraction is
a different pipeline; this connector is the on-ramp for
"a PDF arrived on disk, give me a tracking envelope."

### `salesforce_account_stub`

**Stub** means it accepts a synthetic Salesforce-like dict; it does
NOT call the Salesforce API. Input shape:

```json
{
  "account_id": "001xxx",
  "name": "Acme Health",
  "type": "Customer",
  "industry": "Healthcare",
  "owner_email": "rep@example.com"
}
```

Output: a v3 envelope with `source.source_system = "salesforce"`,
`source.source_kind = "account"`,
`identity.document_type = "account_record"`, `identity.title = name`,
and one `gallounits.units[]` entry per significant input field.

### `invoice_stub`

The canonical **linker-ready** demo. Accepts a synthetic invoice dict
with `invoice_id`, `vendor_name`, `total_amount`, `currency`,
`due_date`, `line_items: [{description, quantity, unit_price, amount}]`.

Output:

- `source.source_system = "internal_invoice_system"`,
  `source.source_kind = "invoice"`.
- `identity.document_type = "invoice"`,
  `identity.title = f"Invoice {invoice_id} — {vendor_name}"`.
- `gallounits.units[]` — one unit per line item with
  `unit_type = "table_row"`, deterministic
  `unit_id = "sha256:<invoice_id>:<line_index>"`, a non-empty
  `text_hash`, and a `content_summary` describing the line.
- `truth_ledger.claims[]` — at least one claim about the invoice total
  with `field_path = "total_amount"` and
  `claim_value_summary = f"{currency} {total_amount}"`.
- `evidence.refs[]` — references the source invoice document.

This is the connector that prompt 04 (linker) consumes as a test
fixture.

## 4. `source.connector_lineage` shape

Every starter connector populates `source.connector_lineage` with the
v2.0 shape (preserved verbatim under v3 — only the parent location
changed):

```json
{
  "schema_version": "gallodoc.connector_lineage.v2.0",
  "connector_sources": [
    {"connector_slug": "invoice_stub", "connector_category": "stub", "status": "active"}
  ],
  "sync_runs": [
    {
      "sync_run_id": "...",
      "connector_slug": "invoice_stub",
      "started_at": "2026-05-16T00:00:00Z",
      "completed_at": "2026-05-16T00:00:01Z",
      "status": "completed",
      "records_seen": 1,
      "records_ingested": 1
    }
  ],
  "record_receipts": [
    {
      "receipt_id": "...",
      "sync_run_id": "...",
      "record_hash": "sha256:...",
      "source_record_id_hash": "sha256:...",
      "gallodoc_ref": "..."
    }
  ]
}
```

The required `sync_runs[]` fields (`sync_run_id`, `connector_slug`,
`started_at`, `status`) come straight from `ConnectorRunReceipt`. The
v2.0 validator enforces these via `_validate_v20_field_ranges`.

The v2.0 `connector_lineage` forbidden-key set (`raw_url`,
`raw_endpoint`, `raw_record`, `record_payload`, `credential`,
`auth_credential`) is enforced by the validator. The SDK never emits
those keys; if a connector author misconfigures one, the projector
strips it.

## 5. CLI

The SDK ships one CLI subcommand, wired into the existing `gallodoc`
binary:

```
gallodoc connector convert \
  --connector <slug> \
  --input <path> \
  --out <path>
```

Reads `<path>` via the named connector, projects each record through
`project_to_open_core`, and writes the result to `<path>`. If the
connector yields multiple records, the output is a JSON array of
envelopes; if one record, a single envelope.

Exit codes: `0` on success, non-zero on bad slug, missing input, or a
write error.

## 6. Privacy invariants

- **No secrets ever land in an envelope.** The
  `_FORBIDDEN_KEY_NAMES` set in
  [`gallodoc/projection/projector.py`](../../gallodoc/projection/projector.py)
  strips `api_key`, `password`, `bearer_token`, `authorization`, etc.
  Every starter connector test asserts no secrets leak.
- **Source record IDs are hashed by default.** Connector receipts use
  `source_record_id_hash` (SHA-256), never raw record IDs. A connector
  may set `source.source_record_id` to the raw value only when
  explicitly authorized by the caller (none of the starter connectors
  do).
- **Example email addresses use `example.com` only.** The v3 validator
  rejects any other domain in non-hash string fields
  (`_EMAIL_DISALLOWED` in `gallodoc/validation/__init__.py`).
- **Connectors must not import platform code.** No `mvp_core.*`, no
  HaloBridge-specific module. Stdlib + the `gallodoc` package only.
  Optional extras (`pypdf` for PDF page count) are guarded with a
  conditional import.

## 7. Forward references

- **Prompt 04 (linker):** consumes envelopes produced by
  `invoice_stub` and `salesforce_account_stub` for linker tests.
- **Prompt 10 (release-gate):** validates the connector test
  fixtures shipped under `tests/v3_0/connectors/` and
  `examples/v3_0/connectors/`.

## 8. Spec compliance summary

- Output: every connector emits a v3-shaped envelope that passes
  `validate_envelope()` from `gallodoc.validation`.
- Provenance: `source.connector_slug` is set, and
  `source.connector_lineage.sync_runs[]` has at least one entry.
- Schema: connectors use the v2.0 `connector_lineage` schema slug
  (`gallodoc.connector_lineage.v2.0`) for the sub-block — the shape is
  unchanged, only the parent location changed.
