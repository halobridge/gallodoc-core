# Connector guide

**Audience:** developers adding a connector that produces v3 envelopes
from a new source system.
**Reading time:** ~7 minutes.
**Companion spec:**
[`docs/specs/gallodoc-core-v3-connector-sdk.md`](../specs/gallodoc-core-v3-connector-sdk.md).

---

## What a connector does

A GalloDoc connector reads records from some upstream source (Salesforce,
a CSV file, a PDF, an SQL query, a Salesforce account, an invoice PDF)
and emits valid `gallodoc-core/v3` envelopes. The connector is
responsible for:

1. **Fetching records** from the upstream source.
2. **Wrapping each record** in a v3 envelope with `source.connector_lineage`
   populated.
3. **Emitting a `ConnectorRunReceipt`** that summarizes what was synced.

The connector is **not** responsible for downstream operations
(classification, extraction, review, linking). Those happen on the
envelope after the connector emits it.

---

## The four interfaces

From `gallodoc.connectors`:

| Type | Purpose |
|---|---|
| `ConnectorSource` | Describes the upstream system (slug, type, endpoint, auth shape). |
| `ConnectorRecord` | One record fetched from the source. |
| `GalloDocConnector` | The connector itself — implements `fetch_records()` and `convert_record()`. |
| `ConnectorRunReceipt` | Summary of a single sync run (record count, errors, timing). |

The five starter connectors that ship with v3.0 live under
`gallodoc/connectors/`:

| Slug | What it converts |
|---|---|
| `generic_json` | Any JSON dict → envelope. Default for ad-hoc use. |
| `csv_row` | A CSV row → envelope. |
| `pdf_file_metadata` | A PDF on disk → envelope (metadata only, no OCR). |
| `salesforce_account_stub` | A synthetic Salesforce account record → envelope. |
| `invoice_stub` | A synthetic invoice record → envelope. |

---

## The 5-minute path: convert one record

```bash
pip install gallodoc
gallodoc connector convert \
  --connector generic_json \
  --input my_data.json \
  --out env.gdoc.json
gallodoc validate env.gdoc.json
```

The first command produces a valid `gallodoc-core/v3` envelope with
`source.connector_lineage` populated. The second confirms it validates.

---

## Writing your own connector

### Skeleton

```python
from gallodoc.connectors import (
    ConnectorSource,
    ConnectorRecord,
    GalloDocConnector,
    ConnectorRunReceipt,
)


class MyConnector(GalloDocConnector):
    slug = "my_connector"

    def source(self) -> ConnectorSource:
        return ConnectorSource(
            slug=self.slug,
            source_system="my_system",
            source_kind="document",
            connector_version="1.0.0",
        )

    def fetch_records(self, *, config: dict) -> list[ConnectorRecord]:
        """Read records from your upstream system.

        Return a list of ConnectorRecord. Pagination, auth, retry are
        the connector's responsibility — the framework does not retry.
        """
        ...

    def convert_record(
        self, record: ConnectorRecord
    ) -> dict:
        """Convert one ConnectorRecord into a v3 envelope.

        Must return a dict that validates as gallodoc-core/v3. Use
        gallodoc.connectors.helpers.build_minimal_envelope() if you
        want a starting scaffold.
        """
        ...
```

### What the framework gives you for free

- `gallodoc.connectors.helpers.build_minimal_envelope(source)` — returns
  a valid v3 envelope skeleton with `source.connector_lineage`
  populated. You fill in `identity`, `purpose`, content-specific
  blocks.
- The CLI `gallodoc connector convert` wires up your connector
  automatically once it's registered in
  `gallodoc.connectors.CONNECTOR_REGISTRY`.
- `ConnectorRunReceipt` is appended to
  `source.connector_lineage.sync_runs[]` on the envelope.

### Required envelope blocks

Every envelope your `convert_record` emits MUST have the 18 required
top-level sections (see
[`docs/specs/gallodoc-core-v3-master-spec.md §2`](../specs/gallodoc-core-v3-master-spec.md)).
The `build_minimal_envelope` helper provides empty-but-shaped defaults
for every one.

### Required `source.connector_lineage` fields

```json
{
  "source": {
    "source_system": "my_system",
    "source_kind": "document",
    "connector_slug": "my_connector",
    "connector_lineage": {
      "schema_version": "gallodoc.connector_lineage.v2.0",
      "connector_sources": [...],
      "sync_runs": [...],
      "record_receipts": [...]
    }
  }
}
```

---

## Privacy contract

Your connector emits envelopes that ship as open-source examples
eventually. The privacy contract:

- **Never include raw secrets, OAuth tokens, API keys, or
  authentication material.** Those live in your runtime config, not
  in the envelope.
- **Never include raw PHI / PII.** SSN-like / MRN-like / email-like
  patterns are flagged by `assert_no_enterprise_leakage`.
- **Never write under `extensions.halobridge.<known_block>`.** 14
  names are banned — see
  [`gallodoc/projection/forbidden.py`](../../gallodoc/projection/forbidden.py).
- **Synthetic data only in examples.** If you're shipping a
  connector example envelope, use synthetic fixtures.

---

## Testing your connector

Add a test file under `tests/v3_0/connectors/` mirroring the existing
five connectors. The minimum surface:

```python
import json
from pathlib import Path

from gallodoc.connectors import get_connector
from gallodoc.validation import validate_envelope


def test_my_connector_produces_valid_envelope(tmp_path: Path) -> None:
    connector = get_connector("my_connector")
    records = connector.fetch_records(config={"fixture_path": "..."})
    assert records, "fetch_records returned nothing"
    env = connector.convert_record(records[0])
    result = validate_envelope(env)
    assert result.valid, result.issues
```

---

## Registering your connector in the CLI

Add an entry to `gallodoc.connectors.CONNECTOR_REGISTRY`:

```python
# gallodoc/connectors/__init__.py
from gallodoc.connectors.my_connector import MyConnector

CONNECTOR_REGISTRY: dict[str, type[GalloDocConnector]] = {
    "generic_json": GenericJSONConnector,
    # ...
    "my_connector": MyConnector,
}
```

After registration, `gallodoc connector convert --connector my_connector`
just works.

---

## What ships with the connector framework

| File | Role |
|---|---|
| `gallodoc/connectors/__init__.py` | Public API + registry. |
| `gallodoc/connectors/base.py` | Base classes. |
| `gallodoc/connectors/helpers.py` | `build_minimal_envelope` and friends. |
| `gallodoc/connectors/cli.py` | The `gallodoc connector convert` subcommand. |
| `examples/v3_0/connectors/` | Five worked examples — input + expected envelope. |
| `tests/v3_0/connectors/` | Per-connector test coverage. |

---

## Further reading

- Spec: [`docs/specs/gallodoc-core-v3-connector-sdk.md`](../specs/gallodoc-core-v3-connector-sdk.md).
- Privacy gate:
  [`gallodoc.projection.safety`](../../gallodoc/projection/safety.py).
- Examples: [`examples/v3_0/connectors/`](../../examples/v3_0/connectors/).
