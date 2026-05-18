"""PDF file metadata connector — file-stat-only, no text extraction."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

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
    hash_path,
    now_iso,
)
from gallodoc.projection import project_to_open_core


class PdfFileMetadataConnector(GalloDocConnector):
    """Extract file-level metadata from a PDF on disk.

    Returns a single record carrying ``file_size_bytes``, ``mtime_iso``,
    ``page_count`` (if ``pypdf`` is installed, else ``None``), and
    ``file_path_hash``. **Does NOT extract PDF text** — that is a
    separate pipeline.
    """

    slug = "pdf_file_metadata"
    version = "3.0.0"

    # ------------------------------------------------------------------
    # read
    # ------------------------------------------------------------------

    def read(self, source: Path | str) -> Iterable[ConnectorRecord]:
        return list(self._read_inner(source))

    def _read_inner(self, source: Path | str):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"pdf_file_metadata: source not found: {path}")
        if not path.is_file():
            raise IsADirectoryError(f"pdf_file_metadata: not a file: {path}")

        stat = os.stat(path)
        mtime_iso = (
            datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        page_count = _read_page_count(path)
        payload = {
            "file_size_bytes": int(stat.st_size),
            "mtime_iso": mtime_iso,
            "page_count": page_count,
            "file_path_hash": hash_path(path),
            "file_name": path.name,
        }
        yield ConnectorRecord(
            record_id=str(path),
            payload=payload,
            raw_source_ref=str(path),
            record_metadata={"filename": path.name},
        )

    # ------------------------------------------------------------------
    # to_envelope
    # ------------------------------------------------------------------

    def to_envelope(self, record: ConnectorRecord) -> dict[str, Any]:
        envelope = build_v3_skeleton()
        envelope["source"]["source_system"] = "filesystem"
        envelope["source"]["source_kind"] = "pdf_file"

        envelope["identity"]["gallodoc_id"] = f"pdf-file:{record.record_id_hash}"
        envelope["identity"]["title"] = record.payload.get("file_name", "")
        envelope["identity"]["document_type"] = "pdf_file"
        envelope["identity"]["mime_type"] = "application/pdf"

        # Page count goes onto identity.* / media.* if present.
        if record.payload.get("page_count") is not None:
            envelope.setdefault("media", {})
            envelope["media"]["kind"] = "binary"
            envelope["media"]["mime_type"] = "application/pdf"
            envelope["media"]["page_count"] = int(record.payload["page_count"])

        # File metadata under extensions stash.
        stash_under_extensions(envelope, self.slug, record.payload)

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


# ---------------------------------------------------------------------------
# Optional pypdf-backed page count
# ---------------------------------------------------------------------------


def _read_page_count(path: Path) -> int | None:
    """Return the PDF page count if ``pypdf`` is installed, else ``None``.

    The connector ships without ``pypdf`` as a hard dependency — page
    count is a "nice to have" enrichment, not a requirement for envelope
    validity.
    """
    try:
        import pypdf  # type: ignore  # noqa: PLC0415
    except ImportError:
        return None
    try:
        reader = pypdf.PdfReader(str(path))
        return len(reader.pages)
    except Exception:  # pragma: no cover — defensive for malformed PDFs
        return None


__all__ = ["PdfFileMetadataConnector"]
