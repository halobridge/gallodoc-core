"""Generic JSON connector — turns a JSON dict, list, or string into v3 envelopes."""

from __future__ import annotations

import json
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
    hash_str,
    now_iso,
)
from gallodoc.projection import project_to_open_core


# Default mapping: input-key → envelope dotted path.
_DEFAULT_FIELD_MAP: dict[str, str] = {
    "id": "identity.gallodoc_id",
    "title": "identity.title",
    "document_type": "identity.document_type",
}


class GenericJsonConnector(GalloDocConnector):
    """Convert generic JSON input into v3 envelopes.

    Accepts a dict, a list of dicts, a JSON string, or a path to a
    file containing either. The connector author can pass a custom
    ``field_map`` to route input keys to specific envelope paths;
    anything not in the map lands under
    ``extensions.connector_input.generic_json``.
    """

    slug = "generic_json"
    version = "3.0.0"

    def __init__(self, field_map: dict[str, str] | None = None) -> None:
        self.field_map: dict[str, str] = (
            dict(field_map) if field_map is not None else dict(_DEFAULT_FIELD_MAP)
        )

    # ------------------------------------------------------------------
    # read
    # ------------------------------------------------------------------

    def read(self, source: Any) -> Iterable[ConnectorRecord]:
        """Parse ``source`` into ``ConnectorRecord``s.

        ``source`` may be:
        - a ``dict`` — emits one record
        - a ``list[dict]`` — emits one record per dict
        - a JSON string — parsed, then handled per type
        - a ``Path`` or path-like ``str`` — file is read and parsed
        """
        return list(self._read_inner(source))

    def _read_inner(self, source: Any) -> Iterator[ConnectorRecord]:
        parsed = self._parse(source)
        raw_ref = self._raw_ref(source)

        if isinstance(parsed, dict):
            yield self._record_from_dict(parsed, raw_ref, index=0)
        elif isinstance(parsed, list):
            for i, item in enumerate(parsed):
                if isinstance(item, dict):
                    yield self._record_from_dict(item, raw_ref, index=i)

    @staticmethod
    def _parse(source: Any) -> Any:
        if isinstance(source, (dict, list)):
            return source
        if isinstance(source, Path):
            return json.loads(source.read_text(encoding="utf-8"))
        if isinstance(source, str):
            # Try path-on-disk first; fall back to JSON string.
            p = Path(source)
            if p.exists() and p.is_file():
                return json.loads(p.read_text(encoding="utf-8"))
            return json.loads(source)
        raise TypeError(
            f"generic_json: unsupported source type {type(source).__name__}"
        )

    @staticmethod
    def _raw_ref(source: Any) -> str | None:
        if isinstance(source, Path):
            return str(source)
        if isinstance(source, str):
            p = Path(source)
            if p.exists():
                return str(p)
        return None

    @staticmethod
    def _record_from_dict(
        payload: dict[str, Any], raw_ref: str | None, *, index: int
    ) -> ConnectorRecord:
        # Use the input's `id` field if present, else a path:index ref,
        # else a deterministic hash of the payload.
        candidate_id = payload.get("id")
        if isinstance(candidate_id, str) and candidate_id:
            record_id = candidate_id
        elif raw_ref:
            record_id = f"{raw_ref}:item:{index}"
        else:
            record_id = hash_str(json.dumps(payload, sort_keys=True, default=str))
        return ConnectorRecord(
            record_id=record_id,
            payload=dict(payload),
            raw_source_ref=raw_ref,
        )

    # ------------------------------------------------------------------
    # to_envelope
    # ------------------------------------------------------------------

    def to_envelope(self, record: ConnectorRecord) -> dict[str, Any]:
        envelope = build_v3_skeleton()
        envelope["source"]["source_system"] = "generic"
        envelope["source"]["source_kind"] = "json"

        consumed = apply_field_map(envelope, record.payload, self.field_map)

        # Default a gallodoc_id if the field map didn't supply one.
        if not envelope["identity"].get("gallodoc_id"):
            envelope["identity"]["gallodoc_id"] = f"generic-json:{record.record_id_hash}"

        # Dump unmapped keys under extensions.connector_input.<slug>.
        unmapped = {k: v for k, v in record.payload.items() if k not in consumed}
        if unmapped:
            stash_under_extensions(envelope, self.slug, unmapped)

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
            source_ref_hash=(
                hash_str(record.raw_source_ref) if record.raw_source_ref else None
            ),
            status="completed",
        )
        populate_connector_lineage(envelope, slug=self.slug, receipt=receipt, record=record)

        # Final projection ensures schema-valid output.
        return project_to_open_core(envelope)


__all__ = ["GenericJsonConnector"]
