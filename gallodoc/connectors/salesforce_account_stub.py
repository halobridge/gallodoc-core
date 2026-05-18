"""Salesforce account stub — turns a synthetic SFDC account dict into a v3 envelope.

**Stub** means this connector does NOT call the Salesforce API. It
accepts a synthetic input dict so adopters can demo the shape without
needing live SFDC credentials.
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


# Fields that, if present, produce a `gallounits.units[]` entry.
_UNIT_FIELDS: tuple[str, ...] = ("name", "type", "industry", "owner_email")


class SalesforceAccountStubConnector(GalloDocConnector):
    """Synthetic Salesforce account → v3 envelope.

    Input shape:

    ```json
    {
      "account_id": "001xxx",
      "name": "Acme Health",
      "type": "Customer",
      "industry": "Healthcare",
      "owner_email": "rep@example.com"
    }
    ```

    The connector does NOT call Salesforce — it accepts synthetic
    input so the SDK demo works offline.
    """

    slug = "salesforce_account_stub"
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
                f"salesforce_account_stub: source must be dict or list[dict], "
                f"got {type(source).__name__}"
            )

        for item in items:
            account_id = item.get("account_id") or item.get("id") or ""
            record_id = (
                account_id
                if isinstance(account_id, str) and account_id
                else f"sfdc-account:{hash_str(repr(sorted(item.items())))}"
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

        envelope["source"]["source_system"] = "salesforce"
        envelope["source"]["source_kind"] = "account"

        title = payload.get("name", "") or "Unnamed account"
        envelope["identity"]["gallodoc_id"] = f"sfdc-account:{record.record_id_hash}"
        envelope["identity"]["title"] = title
        envelope["identity"]["document_type"] = "account_record"

        # gallounits.units[] — one unit per significant field that is
        # present. Each unit gets a deterministic unit_id + text_hash.
        units: list[dict[str, Any]] = []
        for field_name in _UNIT_FIELDS:
            value = payload.get(field_name)
            if value is None or value == "":
                continue
            unit_id = "sha256:" + hashlib.sha256(
                f"{record.record_id}:{field_name}".encode("utf-8")
            ).hexdigest()
            text_hash = "sha256:" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()
            units.append(
                {
                    "unit_id": unit_id,
                    "unit_type": "entity",
                    "semantic_role": f"sfdc_account.{field_name}",
                    "text_hash": text_hash,
                    "content_summary": f"{field_name}: {value}",
                    "evidence_refs": [],
                    "relationship_refs": [],
                    "extractions": {},
                    "validation_refs": [],
                    "ai_usage_refs": [],
                }
            )
        envelope["gallounits"]["units"] = units
        envelope["gallounits"]["unit_strategy"] = "sfdc_account_v1"

        # Stash the full input under extensions so downstream consumers
        # can inspect (forbidden keys are scrubbed by the projector).
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


__all__ = ["SalesforceAccountStubConnector"]
