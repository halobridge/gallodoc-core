"""CSV-row connector — turns each row of a CSV into one v3 envelope."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Iterator

from gallodoc.connectors._envelope import (
    apply_field_map,
    build_v3_skeleton,
    new_sync_run_id,
    populate_connector_lineage,
    stash_under_extensions,
)
from gallodoc.connectors.base import (
    ConnectorRecord,
    ConnectorRunReceipt,
    GalloDocConnector,
    hash_path,
    now_iso,
)
from gallodoc.projection import project_to_open_core


_DEFAULT_COLUMN_MAP: dict[str, str] = {
    "id": "identity.gallodoc_id",
    "title": "identity.title",
}


class CsvRowConnector(GalloDocConnector):
    """Convert each CSV row into a v3 envelope.

    ``source`` is a path to a CSV file (or a path-like string). The
    file is opened with stdlib ``csv.DictReader`` — the first row is
    treated as a header. Each subsequent row yields a record whose
    ``record_id`` is ``f"{filename}:row:{rownum}"``.
    """

    slug = "csv_row"
    version = "3.0.0"

    def __init__(self, column_map: dict[str, str] | None = None) -> None:
        self.column_map: dict[str, str] = (
            dict(column_map) if column_map is not None else dict(_DEFAULT_COLUMN_MAP)
        )

    # ------------------------------------------------------------------
    # read
    # ------------------------------------------------------------------

    def read(self, source: Path | str) -> Iterable[ConnectorRecord]:
        return list(self._read_inner(source))

    def _read_inner(self, source: Path | str) -> Iterator[ConnectorRecord]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"csv_row: source not found: {path}")
        with path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            for rownum, row in enumerate(reader, start=1):
                # csv.DictReader returns OrderedDict-likes — coerce to plain dict.
                payload: dict[str, Any] = {k: v for k, v in row.items() if k is not None}
                record_id = f"{path.name}:row:{rownum}"
                yield ConnectorRecord(
                    record_id=record_id,
                    payload=payload,
                    raw_source_ref=str(path),
                    record_metadata={"row_number": rownum, "filename": path.name},
                )

    # ------------------------------------------------------------------
    # to_envelope
    # ------------------------------------------------------------------

    def to_envelope(self, record: ConnectorRecord) -> dict[str, Any]:
        envelope = build_v3_skeleton()
        envelope["source"]["source_system"] = "csv"
        envelope["source"]["source_kind"] = "csv_row"

        consumed = apply_field_map(envelope, record.payload, self.column_map)

        # Default a gallodoc_id if the column map didn't supply one.
        if not envelope["identity"].get("gallodoc_id"):
            envelope["identity"]["gallodoc_id"] = f"csv-row:{record.record_id_hash}"

        # Unmapped columns → extensions stash + row-number metadata.
        unmapped = {k: v for k, v in record.payload.items() if k not in consumed}
        stash_payload: dict[str, Any] = {"row": unmapped, **record.record_metadata}
        stash_under_extensions(envelope, self.slug, stash_payload)

        # Build + attach lineage.
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
            source_ref_hash=hash_path(record.raw_source_ref or ""),
            status="completed",
        )
        populate_connector_lineage(envelope, slug=self.slug, receipt=receipt, record=record)

        return project_to_open_core(envelope)


__all__ = ["CsvRowConnector"]
