"""Internal helpers — v3 envelope skeleton + field-map application.

Used by every starter connector to produce a valid v3 envelope. The
final ``project_to_open_core`` pass guarantees validity even if a
connector author misconfigures a field.
"""

from __future__ import annotations

import copy
import hashlib
import uuid
from typing import Any

from gallodoc.connectors.base import ConnectorRecord, ConnectorRunReceipt


# ---------------------------------------------------------------------------
# v3 skeleton — all 18 required sections present with minimal valid values.
# ---------------------------------------------------------------------------


def build_v3_skeleton() -> dict[str, Any]:
    """Return a fresh dict carrying every required v3 section.

    Required leaf fields are populated with minimal valid values
    (``""``, ``[]``, ``{}``, ``false``, ``0``) so the validator's
    structural checks pass. Callers overlay connector-specific data on
    top of this skeleton.
    """
    return {
        "schema_version": "gallodoc-core/v3",
        "identity": {
            "gallodoc_id": "",
            "schema_version": "gallodoc-core/v3",
        },
        "source": {
            "source_system": "",
            "source_kind": "",
            "readiness_status": "ready",
        },
        "purpose": {
            "primary_intent": "ingest",
            "workflow_intent": "ingest",
        },
        "lifecycle": {
            "available": False,
            "current_status": "",
            "stages": [],
        },
        "activity": {
            "available": False,
            "event_count": 0,
            "counts_by_type": {},
            "latest_events": [],
        },
        "relationships": {
            "schema_version": "gallodoc.relationships.v3.0",
            "relationships": [],
            "relationship_evidence": [],
            "relationship_decisions": [],
        },
        "evidence": {
            "count": 0,
            "refs": [],
        },
        "validations": {
            "contradictions": [],
            "packet_findings": [],
            "model_disagreements": [],
        },
        "security": {
            "phi_detected": False,
            "phi_categories": [],
            "phi_risk_level": "none",
            "encrypted": False,
            "encryption_backend": None,
            "encryption_key_id": None,
            "encrypted_fields": [],
            "masked_fields": [],
            "redaction_policy": None,
            "raw_export_allowed": True,
            "encryption_policy_status": "not_required",
            "last_phi_scan_at": None,
            "last_encrypted_at": None,
        },
        "exports": [],
        "extensions": {},
        "ai_usage": {
            "summary": {
                "total_runs": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "estimated_total_cost": 0.0,
                "currency": "USD",
            },
            "runs": [],
        },
        "gallounits": {
            "unit_strategy": "connector_v1",
            "units": [],
        },
        "certification": {
            "status": "none",
            "certification_type": "none",
        },
        "gstp": {
            "package_id": "",
            "package_type": "none",
            "status": "not_created",
        },
        "truth_ledger": {
            "available": False,
            "truth_state": "uncertified",
            "claims": [],
            "events": [],
        },
        "trust": {
            "schema_version": "gallodoc.trust.v3.0",
            "components": [],
            "drivers": [],
            "blockers": [],
            "warnings": [],
            "decision_gates": [],
            "policy_outcomes": [],
            "action_recommendations": [],
            "decision_receipts": [],
        },
    }


# ---------------------------------------------------------------------------
# Field-map application
# ---------------------------------------------------------------------------


def apply_field_map(
    envelope: dict[str, Any],
    payload: dict[str, Any],
    field_map: dict[str, str],
) -> set[str]:
    """Route ``payload`` keys into ``envelope`` according to ``field_map``.

    ``field_map`` is ``{input_key: "section.subkey.path"}``. Returns the
    set of input keys that were consumed (the connector dumps the
    remaining keys under ``extensions.connector_input.<slug>``).
    """
    consumed: set[str] = set()
    for input_key, dotted_path in field_map.items():
        if input_key not in payload:
            continue
        _set_path(envelope, dotted_path, payload[input_key])
        consumed.add(input_key)
    return consumed


def _set_path(envelope: dict[str, Any], dotted_path: str, value: Any) -> None:
    """Set a dotted path inside ``envelope`` to ``value``.

    Intermediate dicts are created if they do not exist. The leaf is
    overwritten unconditionally — connectors are expected to use
    field maps that don't collide with one another.
    """
    if not dotted_path:
        return
    parts = dotted_path.split(".")
    cursor: Any = envelope
    for part in parts[:-1]:
        if not isinstance(cursor, dict):
            return
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    if isinstance(cursor, dict):
        cursor[parts[-1]] = value


# ---------------------------------------------------------------------------
# Connector lineage
# ---------------------------------------------------------------------------


def populate_connector_lineage(
    envelope: dict[str, Any],
    *,
    slug: str,
    receipt: ConnectorRunReceipt,
    record: ConnectorRecord,
    record_hash: str | None = None,
) -> None:
    """Populate ``source.connector_slug``, ``source.sync_run_id``, and
    ``source.connector_lineage`` for one record.

    The shape matches the v2.0 ``connector_lineage`` block —
    ``connector_sources[]``, ``sync_runs[]``, ``record_receipts[]``.
    Forbidden keys (``raw_url``, ``raw_endpoint``, ``raw_record``,
    ``record_payload``, ``credential``, ``auth_credential``) are never
    emitted here; the projector strips them defensively even if a
    subclass adds them.
    """
    source = envelope.setdefault("source", {})
    source.setdefault("connector_slug", slug)
    source.setdefault("sync_run_id", receipt.sync_run_id)

    record_hash_value = record_hash or _record_hash(record)

    source["connector_lineage"] = {
        "schema_version": "gallodoc.connector_lineage.v2.0",
        "connector_sources": [
            {
                "connector_slug": slug,
                "connector_category": "open_sdk",
                "status": "active",
            }
        ],
        "sync_runs": [receipt.to_dict()],
        "record_receipts": [
            {
                "receipt_id": f"rcpt-{receipt.sync_run_id}",
                "sync_run_id": receipt.sync_run_id,
                "record_hash": record_hash_value,
                "source_record_id_hash": record.record_id_hash,
                "gallodoc_ref": envelope.get("identity", {}).get("gallodoc_id", ""),
            }
        ],
    }


def _record_hash(record: ConnectorRecord) -> str:
    """SHA-256 over a canonical JSON dump of the record's payload."""
    import json

    body = json.dumps(record.payload, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def stash_under_extensions(
    envelope: dict[str, Any],
    slug: str,
    payload: dict[str, Any],
) -> None:
    """Drop ``payload`` under ``extensions.connector_input.<slug>``.

    Used to carry the raw (post-projection-scrub) input for downstream
    consumers that want to introspect what the connector saw.
    """
    ext = envelope.setdefault("extensions", {})
    bucket = ext.setdefault("connector_input", {})
    bucket[slug] = copy.deepcopy(payload)


# ---------------------------------------------------------------------------
# Run-receipt convenience
# ---------------------------------------------------------------------------


def new_sync_run_id(slug: str) -> str:
    """Return a fresh ``sync-<slug>-<uuid4>`` identifier."""
    return f"sync-{slug}-{uuid.uuid4().hex[:12]}"


__all__ = [
    "apply_field_map",
    "build_v3_skeleton",
    "new_sync_run_id",
    "populate_connector_lineage",
    "stash_under_extensions",
]
