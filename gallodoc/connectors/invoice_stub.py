"""Invoice stub — the canonical linker-ready demo connector.

Accepts a synthetic invoice dict with line items and emits a v3
envelope with populated ``gallounits.units[]`` (one per line item) and
a ``truth_ledger.claims[]`` entry asserting the invoice total. Prompt 04
(linker) consumes envelopes produced by this connector.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Iterator

from gallodoc.connectors._envelope import (
    build_v3_skeleton,
    new_sync_run_id,
    populate_connector_lineage,
    stash_under_extensions,
)
from gallodoc.connectors.base import (
    ConnectorRecord,
    ConnectorRunReceipt,
    GalloDocConnector,
    hash_str,
    now_iso,
)
from gallodoc.projection import project_to_open_core


class InvoiceStubConnector(GalloDocConnector):
    """Synthetic invoice → v3 envelope, linker-ready.

    Input shape:

    ```json
    {
      "invoice_id": "INV-001",
      "vendor_name": "Example Vendor LLC",
      "total_amount": 1234.56,
      "currency": "USD",
      "due_date": "2026-06-01",
      "line_items": [
        {"description": "Widget A", "quantity": 2, "unit_price": 10.00, "amount": 20.00}
      ]
    }
    ```
    """

    slug = "invoice_stub"
    version = "3.0.0"

    # ------------------------------------------------------------------
    # read
    # ------------------------------------------------------------------

    def read(self, source: dict[str, Any] | list[dict[str, Any]]) -> Iterable[ConnectorRecord]:
        return list(self._read_inner(source))

    def _read_inner(
        self, source: dict[str, Any] | list[dict[str, Any]]
    ) -> Iterator[ConnectorRecord]:
        items: list[dict[str, Any]]
        if isinstance(source, dict):
            items = [source]
        elif isinstance(source, list):
            items = [s for s in source if isinstance(s, dict)]
        else:
            raise TypeError(
                f"invoice_stub: source must be dict or list[dict], "
                f"got {type(source).__name__}"
            )
        for item in items:
            invoice_id = item.get("invoice_id") or ""
            record_id = (
                invoice_id
                if isinstance(invoice_id, str) and invoice_id
                else f"invoice:{hash_str(repr(sorted(item.items())))}"
            )
            yield ConnectorRecord(
                record_id=record_id,
                payload=dict(item),
                raw_source_ref=None,
            )

    # ------------------------------------------------------------------
    # to_envelope
    # ------------------------------------------------------------------

    def to_envelope(self, record: ConnectorRecord) -> dict[str, Any]:
        envelope = build_v3_skeleton()
        payload = record.payload
        invoice_id = str(payload.get("invoice_id", "")) or record.record_id
        vendor_name = str(payload.get("vendor_name", "")) or "Unknown vendor"
        currency = str(payload.get("currency", "USD")) or "USD"
        total_amount = payload.get("total_amount", 0)
        line_items = payload.get("line_items") or []

        # Source.
        envelope["source"]["source_system"] = "internal_invoice_system"
        envelope["source"]["source_kind"] = "invoice"

        # Identity.
        envelope["identity"]["gallodoc_id"] = f"invoice:{record.record_id_hash}"
        envelope["identity"]["title"] = f"Invoice {invoice_id} — {vendor_name}"
        envelope["identity"]["document_type"] = "invoice"

        # gallounits — one unit per line item.
        units: list[dict[str, Any]] = []
        for idx, line in enumerate(line_items):
            if not isinstance(line, dict):
                continue
            unit_seed = f"{invoice_id}:{idx}"
            unit_id = "sha256:" + hashlib.sha256(unit_seed.encode("utf-8")).hexdigest()
            # text_hash is over the canonical text of the line item.
            description = str(line.get("description", ""))
            quantity = line.get("quantity", "")
            unit_price = line.get("unit_price", "")
            amount = line.get("amount", "")
            canonical_text = f"{description}|{quantity}|{unit_price}|{amount}"
            text_hash = "sha256:" + hashlib.sha256(
                canonical_text.encode("utf-8")
            ).hexdigest()
            units.append(
                {
                    "unit_id": unit_id,
                    "unit_type": "table",
                    "semantic_role": "invoice_line_item",
                    "text_hash": text_hash,
                    "content_summary": (
                        f"{description}: {quantity} x {unit_price} = {amount}"
                    ),
                    "evidence_refs": [],
                    "relationship_refs": [],
                    "extractions": {
                        "line_index": idx,
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "amount": amount,
                    },
                    "validation_refs": [],
                    "ai_usage_refs": [],
                }
            )
        envelope["gallounits"]["units"] = units
        envelope["gallounits"]["unit_strategy"] = "invoice_line_items_v1"

        # truth_ledger — claim about the total.
        claim_id = "claim-" + hashlib.sha256(
            f"{invoice_id}:total_amount".encode("utf-8")
        ).hexdigest()[:16]
        envelope["truth_ledger"]["available"] = True
        envelope["truth_ledger"]["claims"] = [
            {
                "claim_id": claim_id,
                "field_path": "total_amount",
                "claim_value_summary": f"{currency} {total_amount}",
                "status": "proposed",
                "confidence": 0.85,
                "evidence_refs": [],
                "created_by": f"{self.slug}/{self.version}",
                "created_at": now_iso(),
            }
        ]

        # evidence — reference back to the source invoice document.
        envelope["evidence"]["count"] = 1
        envelope["evidence"]["refs"] = [
            {
                "evidence_id": "ev-" + record.record_id_hash[len("sha256:"):][:16],
                "evidence_kind": "invoice_document",
                "source_ref": f"invoice_id:{invoice_id}",
                "summary": f"Source invoice {invoice_id} from {vendor_name}",
            }
        ]

        # Stash full input.
        stash_under_extensions(envelope, self.slug, payload)

        # Lineage.
        started = now_iso()
        receipt = ConnectorRunReceipt(
            connector_slug=self.slug,
            connector_version=self.version,
            sync_run_id=new_sync_run_id(self.slug),
            started_at=started,
            completed_at=started,
            record_count=1,
            success_count=1,
            failed_count=0,
            source_ref_hash=None,
            status="completed",
        )
        populate_connector_lineage(envelope, slug=self.slug, receipt=receipt, record=record)

        return project_to_open_core(envelope)


__all__ = ["InvoiceStubConnector"]
