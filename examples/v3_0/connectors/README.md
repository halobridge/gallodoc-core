# GalloDoc v3 — Open Connector SDK examples

Each pair below shows what one of the five starter connectors emits
when fed synthetic input. The output files are **stabilized**:
volatile fields (`started_at`, `completed_at`, `sync_run_id`,
`mtime_iso`, `file_size_bytes`) are replaced with deterministic
placeholders so the examples are diffable across runs. Real connector
runs populate these with live values.

| Input | Output | What it demonstrates |
|---|---|---|
| [`generic_json_input.json`](generic_json_input.json) | [`generic_json_output.gdoc.json`](generic_json_output.gdoc.json) | One JSON dict → one v3 envelope. Mapped fields land under `identity.*`; unmapped keys (e.g. `tags`, `summary`) land under `extensions.connector_input.generic_json`. |
| [`csv_row_input.csv`](csv_row_input.csv) | [`csv_row_output.gdoc.json`](csv_row_output.gdoc.json) | First row of a 3-row CSV → one envelope. `record_id` is `filename:row:N`; remaining columns land in `extensions.connector_input.csv_row.row`. |
| [`pdf_file_metadata_input.pdf`](pdf_file_metadata_input.pdf) | [`pdf_file_metadata_output.gdoc.json`](pdf_file_metadata_output.gdoc.json) | PDF on disk → envelope with `mime_type: "application/pdf"`, file metadata under extensions, and (if `pypdf` is installed) `media.page_count`. The tiny PDF here is 86 bytes. |
| [`salesforce_account_stub_input.json`](salesforce_account_stub_input.json) | [`salesforce_account_stub_output.gdoc.json`](salesforce_account_stub_output.gdoc.json) | Synthetic Salesforce account → envelope with `source.source_system="salesforce"`, one `gallounits.units[]` entry per significant field. |
| [`invoice_stub_input.json`](invoice_stub_input.json) | [`invoice_stub_output.gdoc.json`](invoice_stub_output.gdoc.json) | Synthetic invoice → linker-ready envelope. Each line item becomes one `gallounits.units[]` entry with a deterministic `unit_id`; `truth_ledger.claims[]` has the total. |

## Reproduce

After `pip install -e .` from `opensource/gallodoc-core/`:

```bash
gallodoc connector convert --connector generic_json \
  --input examples/v3_0/connectors/generic_json_input.json \
  --out /tmp/generic_json_out.gdoc.json

gallodoc connector convert --connector csv_row \
  --input examples/v3_0/connectors/csv_row_input.csv \
  --out /tmp/csv_row_out.gdoc.json

gallodoc connector convert --connector pdf_file_metadata \
  --input examples/v3_0/connectors/pdf_file_metadata_input.pdf \
  --out /tmp/pdf_file_metadata_out.gdoc.json

gallodoc connector convert --connector salesforce_account_stub \
  --input examples/v3_0/connectors/salesforce_account_stub_input.json \
  --out /tmp/salesforce_account_stub_out.gdoc.json

gallodoc connector convert --connector invoice_stub \
  --input examples/v3_0/connectors/invoice_stub_input.json \
  --out /tmp/invoice_stub_out.gdoc.json
```

Each output validates under `gallodoc validate <path>`.

## Privacy invariants

- All inputs use synthetic data. Email addresses are `@example.com`
  only. Account IDs / invoice IDs use the `EX` infix to mark them
  obviously synthetic.
- No real customer or vendor names. No real PHI/PII. No real
  filesystem paths in the committed PDF output (the `file_path_hash`
  in the PDF output is over a synthetic path).
