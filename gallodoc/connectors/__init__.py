"""Open connector SDK for ``gallodoc-core/v3`` envelopes.

Each connector adapts input from an external system into a valid
``gallodoc-core/v3`` envelope by routing through
``gallodoc.projection.project_to_open_core``. The CLI dispatches by
connector slug (see ``gallodoc/connectors/cli.py``).

See ``docs/specs/gallodoc-core-v3-connector-sdk.md`` for the contract.
"""

from gallodoc.connectors.base import (
    ConnectorRecord,
    ConnectorRunReceipt,
    GalloDocConnector,
    hash_path,
    hash_str,
    now_iso,
)
from gallodoc.connectors.csv_row import CsvRowConnector
from gallodoc.connectors.generic_json import GenericJsonConnector
from gallodoc.connectors.invoice_stub import InvoiceStubConnector
from gallodoc.connectors.pdf_file_metadata import PdfFileMetadataConnector
from gallodoc.connectors.salesforce_account_stub import SalesforceAccountStubConnector


# Connector registry — keyed by slug. The CLI dispatches by this map.
# Keep alphabetical for deterministic --help output.
CONNECTORS: dict[str, type[GalloDocConnector]] = {
    "csv_row": CsvRowConnector,
    "generic_json": GenericJsonConnector,
    "invoice_stub": InvoiceStubConnector,
    "pdf_file_metadata": PdfFileMetadataConnector,
    "salesforce_account_stub": SalesforceAccountStubConnector,
}


__all__ = [
    "CONNECTORS",
    "ConnectorRecord",
    "ConnectorRunReceipt",
    "CsvRowConnector",
    "GalloDocConnector",
    "GenericJsonConnector",
    "InvoiceStubConnector",
    "PdfFileMetadataConnector",
    "SalesforceAccountStubConnector",
    "hash_path",
    "hash_str",
    "now_iso",
]
