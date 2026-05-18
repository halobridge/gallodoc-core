"""Open connector SDK — base interfaces.

Each connector adapts input from an external system into a valid
``gallodoc-core/v3`` envelope. The CLI dispatches by connector slug.

See ``docs/specs/gallodoc-core-v3-connector-sdk.md`` for the contract.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator


@dataclass
class ConnectorRecord:
    """A single record from a connector source after parsing.

    Connectors emit these to ``to_envelope``. Stable shape across all
    connectors so the linker, validator, and downstream consumers can
    treat connector output uniformly.
    """

    record_id: str
    """Canonical id for the record. Free-form per connector — the
    invoice connector uses ``invoice_id``, the CSV connector uses
    ``filename:row:N``, the PDF connector uses the file path, etc."""

    payload: dict[str, Any]
    """The parsed record body. The connector's ``to_envelope`` reads
    fields off this dict to populate the envelope."""

    raw_source_ref: str | None = None
    """Opaque reference to the source location — a path with row
    number, a URL hash, etc. Carried in lineage receipts."""

    record_metadata: dict[str, Any] = field(default_factory=dict)
    """Per-record metadata (e.g. CSV row number, PDF file size).
    Connectors may use this to populate
    ``extensions.connector_input.<slug>``."""

    @property
    def record_id_hash(self) -> str:
        """SHA-256 of ``record_id``, prefixed ``sha256:``. Used in
        ``source.connector_lineage.record_receipts[].source_record_id_hash``.
        Deterministic — same ``record_id`` always produces the same
        hash."""
        return "sha256:" + hashlib.sha256(self.record_id.encode("utf-8")).hexdigest()


@dataclass
class ConnectorRunReceipt:
    """Record of a connector run.

    Hashes and counts only — no raw record content. Used as the
    ``source.connector_lineage.sync_runs[]`` entry the connector
    publishes alongside its envelope output.
    """

    connector_slug: str
    connector_version: str
    sync_run_id: str
    started_at: str
    """ISO-8601 RFC 3339 UTC, e.g. ``"2026-05-16T00:00:00Z"``."""
    completed_at: str
    """ISO-8601 RFC 3339 UTC."""
    record_count: int
    success_count: int
    failed_count: int
    source_ref_hash: str | None = None
    """SHA-256 hash of the source location (file path, URL, etc.).
    ``None`` if the run did not have a stable source ref."""
    status: str = "completed"
    """``completed`` | ``failed`` | ``partial``. Matches the
    v2.0 ``connector_lineage.sync_runs[].status`` field."""

    def to_dict(self) -> dict[str, Any]:
        """Render as a dict suitable for
        ``source.connector_lineage.sync_runs[]``.

        Keys match the v2.0 ``connector_lineage`` shape: ``sync_run_id``,
        ``connector_slug``, ``started_at``, ``status`` are required;
        the others are additive.
        """
        return {
            "sync_run_id": self.sync_run_id,
            "connector_slug": self.connector_slug,
            "connector_version": self.connector_version,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "record_count": self.record_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "source_ref_hash": self.source_ref_hash,
            "status": self.status,
        }


class GalloDocConnector(ABC):
    """Open connector SDK base class.

    Subclasses override ``slug``, ``version``, ``read``, and
    ``to_envelope``. The default ``to_envelopes`` composes the two —
    most concrete connectors won't need to override it.
    """

    slug: str = ""
    """Stable connector slug, used in ``source.connector_slug`` and in
    the ``CONNECTORS`` registry. Override in subclass."""

    version: str = ""
    """Connector version (semver). Recorded in lineage. Override in
    subclass."""

    @abstractmethod
    def read(self, source: Any) -> Iterable[ConnectorRecord]:
        """Parse input ``source`` into records.

        ``source`` is connector-specific — a file path for `csv_row`
        and `pdf_file_metadata`, a dict / JSON string for
        `generic_json`, a dict for the stub connectors.
        """

    @abstractmethod
    def to_envelope(self, record: ConnectorRecord) -> dict[str, Any]:
        """Turn one record into a v3 envelope.

        Implementations must call
        ``gallodoc.projection.project_to_open_core`` on the produced
        envelope before returning so the result is a
        guaranteed-valid v3 envelope.
        """

    def to_envelopes(self, source: Any) -> Iterator[dict[str, Any]]:
        """Compose ``read`` + ``to_envelope`` for the common case."""
        for record in self.read(source):
            yield self.to_envelope(record)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def now_iso() -> str:
    """Return current UTC time as ISO-8601 ending in ``Z``.

    Used to populate ``started_at`` / ``completed_at`` on lineage
    receipts. We strip ``+00:00`` so the string is short and matches
    the RFC 3339 ``Z`` convention.
    """
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def hash_str(value: str) -> str:
    """Return ``sha256:<hex>`` for the UTF-8 bytes of ``value``."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_path(path: str | Path) -> str:
    """Return ``sha256:<hex>`` over the stringified path.

    The path itself is hashed (not the file's contents) — this is used
    as a stable lineage ``source_ref_hash`` without leaking the raw
    filesystem location.
    """
    return hash_str(str(path))


__all__ = [
    "ConnectorRecord",
    "ConnectorRunReceipt",
    "GalloDocConnector",
    "now_iso",
    "hash_str",
    "hash_path",
]
