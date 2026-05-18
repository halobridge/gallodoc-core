"""Envelope integration for embeddings.

``apply_embeddings(envelope, adapter, purpose)`` is the single entry
point. It reads ``gallounits.units[]``, generates one embedding per
unit with a ``content_summary``, and appends one ``EmbeddingRecord``
per unit to ``gallounits.embeddings[]``.

Privacy posture (full detail in
``docs/specs/gallodoc-core-v3-embeddings.md``):

- Raw vector floats NEVER ship by default. The default storage shape
  records only metadata + a deterministic hash + an opaque ref.
- ``include_vector=True`` raises ``EnterpriseLeakageError`` unless
  ``envelope["safety_profile"]["raw_vectors_stored"] == True``.

Idempotency: re-running with the same (adapter, purpose) appends only
NEW embeddings — units whose deterministic ``embedding_id`` already
exists in ``gallounits.embeddings[]`` are skipped.

Projection: the input envelope is run through
``project_to_open_core`` BEFORE embeddings are attached. The resulting
envelope is then mutated in place. Projecting AFTER attachment would
strip ``raw_vector`` (it's in the global forbidden-keys set on the
projector), which would defeat the authorized opt-in.
"""

from __future__ import annotations

import hashlib
from typing import Any

from gallodoc.projection import project_to_open_core
from gallodoc.projection.safety import EnterpriseLeakageError
from gallodoc.semantic.embeddings.base import (
    EmbeddingAdapter,
    EmbeddingRecord,
    hash_vector,
    now_iso,
    validate_purpose,
)


def _embedding_id_for(unit_id: str, purpose: str, model_id: str) -> str:
    """Deterministic ``embedding_id`` for a (unit, purpose, model) triple."""
    raw = f"{unit_id}::{purpose}::{model_id}"
    return "emb_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _model_hash_or_id(model_id: str) -> str:
    """Opaque ``model_hash_or_id`` derived from the model identifier.

    Real consumers can replace this with a cryptographic hash of the
    actual model weights when known. For the open-source reference,
    we hash the model_id string deterministically.
    """
    return "sha256:" + hashlib.sha256(model_id.encode("utf-8")).hexdigest()


def apply_embeddings(
    envelope: dict[str, Any],
    adapter: EmbeddingAdapter,
    purpose: str,
    *,
    include_vector: bool = False,
) -> dict[str, Any]:
    """Attach embeddings to ``gallounits.embeddings[]``.

    Mutates and returns the input envelope (in place after projection).

    Args:
        envelope: A v3 envelope (or v3-shaped input). Run through
            ``project_to_open_core`` defensively before attachment.
        adapter: Any ``EmbeddingAdapter`` implementation.
        purpose: One of the closed ``PURPOSE_ENUM`` values.
        include_vector: When ``True``, ship the raw vector floats inline.
            Requires ``envelope["safety_profile"]["raw_vectors_stored"]``
            to be ``True``; otherwise raises ``EnterpriseLeakageError``.

    Returns:
        The modified envelope.

    Raises:
        ValueError: If ``purpose`` is not in ``PURPOSE_ENUM``.
        EnterpriseLeakageError: If ``include_vector=True`` without
            ``safety_profile.raw_vectors_stored == True``.
    """
    # Spec rule: purpose validation up front.
    validate_purpose(purpose)

    # Spec rule: --include-vector requires explicit producer authorization
    # via safety_profile.raw_vectors_stored. We check on the INPUT
    # envelope before projection — projection deepcopies, so reading
    # safety_profile here keeps the check honest.
    if include_vector:
        sp = envelope.get("safety_profile") if isinstance(envelope, dict) else None
        authorized = isinstance(sp, dict) and sp.get("raw_vectors_stored") is True
        if not authorized:
            raise EnterpriseLeakageError(
                "apply_embeddings: include_vector=True requires "
                "envelope['safety_profile']['raw_vectors_stored'] == True; "
                "raw vectors NEVER ship by default."
            )

    # Project the input first so the working envelope is guaranteed-valid
    # v3 shape. (Forbidden keys stripped, banned halobridge keys removed,
    # schema_version set.) We then mutate this projected copy — embeddings
    # attached AFTER projection so that raw_vector survives when authorized.
    working = project_to_open_core(envelope)

    gallounits = working.setdefault("gallounits", {})
    if not isinstance(gallounits, dict):
        # Defensive — shouldn't happen post-projection, but keep the
        # function total.
        gallounits = {"unit_strategy": "gallounit_v1", "units": []}
        working["gallounits"] = gallounits

    units = gallounits.get("units")
    if not isinstance(units, list):
        units = []
        gallounits["units"] = units

    embeddings = gallounits.get("embeddings")
    if not isinstance(embeddings, list):
        embeddings = []
        gallounits["embeddings"] = embeddings

    # Existing IDs — idempotency check.
    existing_ids: set[str] = set()
    for entry in embeddings:
        if isinstance(entry, dict):
            eid = entry.get("embedding_id")
            if isinstance(eid, str):
                existing_ids.add(eid)

    # Collect (unit, content_summary, embedding_id) for the units that
    # need embedding. Skip units without content_summary (the embedding
    # source) and units whose deterministic id is already present.
    to_embed: list[tuple[str, str, str]] = []
    for unit in units:
        if not isinstance(unit, dict):
            continue
        unit_id = unit.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id:
            continue
        summary = unit.get("content_summary")
        if not isinstance(summary, str) or not summary:
            continue
        eid = _embedding_id_for(unit_id, purpose, adapter.model_id)
        if eid in existing_ids:
            continue
        to_embed.append((unit_id, summary, eid))

    if not to_embed:
        return working

    # Batch-embed for efficiency. The adapter's contract is that
    # ``embed([])`` returns ``[]`` so the empty case is already
    # handled above.
    vectors = adapter.embed([summary for (_uid, summary, _eid) in to_embed])

    model_hash = _model_hash_or_id(adapter.model_id)
    created_at = now_iso()

    for (unit_id, _summary, eid), vector in zip(to_embed, vectors):
        # Resolve dimensions per-vector — handles adapters whose
        # ``dimensions`` is only known after first ``embed()`` call.
        dims = adapter.dimensions if adapter.dimensions > 0 else len(vector)
        record = EmbeddingRecord(
            embedding_id=eid,
            unit_id=unit_id,
            model_id=adapter.model_id,
            model_hash_or_id=model_hash,
            dimensions=dims,
            vector_ref=f"opaque://store/{eid}",
            embedding_hash=hash_vector(list(vector)),
            purpose=purpose,
            created_at=created_at,
            raw_vector=list(vector) if include_vector else None,
        )
        embeddings.append(record.to_dict())
        existing_ids.add(eid)

    return working


__all__ = ["apply_embeddings"]
