"""v1 -> v3 migration helper.

Applies the three v3 envelope transforms locked in
``docs/v3-design/07_decisions.md``:

1. **Flat trust** (Decision 2): merge ``trust_score.*`` + ``trust_decision.*``
   into the flat ``trust`` block. No nested ``trust.score`` /
   ``trust.decision``.
2. **Relationship status injection** (Decision 3): every entry in
   ``relationships`` gets ``status: "confirmed"`` and
   ``discovered_by: "v1_migration"`` if missing. Pre-existing v1
   relationships are conceptually human-confirmed.
3. **Q5 fix**: promote 13 v1.2–v1.6 compliance blocks from
   ``extensions.halobridge.<name>`` to top level. Top-level wins on
   conflict (the double-emission bug usually emits identical content,
   and the v3 spec puts the canonical home at top level).

Idempotent: ``migrate_v1_to_v3(migrate_v1_to_v3(env))`` produces the
same result as one pass. Already-v3 envelopes pass through unchanged
(except for the ``schema_version`` set at the end).
"""

from __future__ import annotations

import copy
from typing import Any

from gallodoc.projection.forbidden import V12_V16_COMPLIANCE_BLOCKS


_TRUST_BLOCK_SCHEMA_VERSION = "gallodoc.trust.v3.0"


def _ensure_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _ensure_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _merge_flat_trust(envelope: dict[str, Any]) -> None:
    """Transform 1 — flat trust (Decision 2).

    Mutates ``envelope`` in place. Merges v1 ``trust_score.*`` and v1.5
    ``trust_decision.*`` into the flat ``trust`` block. Also drains
    ``extensions.halobridge.trust_decision`` (the v1.5 amendment that
    was double-emitted under extensions per the Q5 bug) — top-level
    wins on conflict. Deletes the source ``trust_score`` /
    ``trust_decision`` keys at the end.

    If neither source exists AND no existing ``trust`` block is present,
    this is a no-op. If the envelope already has a (possibly partial)
    flat ``trust`` block, the migrator merges its arrays with the v1.x
    sources rather than overwriting — supports re-runs on partially
    migrated envelopes.
    """
    # If trust_decision lives under extensions.halobridge (the Q5 bug
    # location) and no top-level copy exists, promote it now so the merge
    # below treats it as a source.
    extensions = envelope.get("extensions")
    if isinstance(extensions, dict):
        halobridge = extensions.get("halobridge")
        if isinstance(halobridge, dict) and "trust_decision" in halobridge:
            ext_td = halobridge["trust_decision"]
            if "trust_decision" not in envelope:
                envelope["trust_decision"] = ext_td
            # Either way the extensions copy is consumed.
            halobridge.pop("trust_decision", None)
            if not halobridge:
                extensions.pop("halobridge", None)

    has_score = isinstance(envelope.get("trust_score"), dict)
    has_decision = isinstance(envelope.get("trust_decision"), dict)
    has_existing_trust = isinstance(envelope.get("trust"), dict)

    if not (has_score or has_decision or has_existing_trust):
        # v3 requires a `trust` block. Inject an empty-but-shaped flat
        # trust block so the migrated envelope satisfies v3's required-
        # sections rule. This is part of the migration contract — v1
        # envelopes have no notion of a flat trust block, but the v3
        # validator requires one.
        envelope["trust"] = {
            "schema_version": _TRUST_BLOCK_SCHEMA_VERSION,
            "components": [],
            "drivers": [],
            "blockers": [],
            "warnings": [],
            "decision_gates": [],
            "policy_outcomes": [],
            "action_recommendations": [],
            "decision_receipts": [],
        }
        return

    # Start from any existing flat trust block (idempotency / partial
    # migration support). Drop nested score/decision objects defensively —
    # the v3 trust block is flat (Decision 2).
    existing = _ensure_dict(envelope.get("trust"))
    existing.pop("score", None)
    existing.pop("decision", None)

    trust: dict[str, Any] = {
        "schema_version": _TRUST_BLOCK_SCHEMA_VERSION,
        "components": _ensure_list(existing.get("components")),
        "drivers": _ensure_list(existing.get("drivers")),
        "blockers": _ensure_list(existing.get("blockers")),
        "warnings": _ensure_list(existing.get("warnings")),
        "decision_gates": _ensure_list(existing.get("decision_gates")),
        "policy_outcomes": _ensure_list(existing.get("policy_outcomes")),
        "action_recommendations": _ensure_list(existing.get("action_recommendations")),
        "decision_receipts": _ensure_list(existing.get("decision_receipts")),
    }

    # Carry over any extra fields the existing trust block already had
    # (forward-compat — Codex 02 only knows the 8 arrays + schema_version,
    # but downstream tools may have already added more).
    for k, v in existing.items():
        if k not in trust:
            trust[k] = v

    if has_score:
        score = envelope["trust_score"]
        trust["components"].extend(_ensure_list(score.get("components")))
        trust["drivers"].extend(_ensure_list(score.get("drivers")))
        trust["blockers"].extend(_ensure_list(score.get("blockers")))
        trust["warnings"].extend(_ensure_list(score.get("warnings")))

    if has_decision:
        decision = envelope["trust_decision"]
        trust["decision_gates"].extend(_ensure_list(decision.get("gates")))
        trust["policy_outcomes"].extend(_ensure_list(decision.get("policy_outcomes")))
        trust["action_recommendations"].extend(_ensure_list(decision.get("action_recommendations")))
        trust["decision_receipts"].extend(_ensure_list(decision.get("decision_receipts")))

    envelope["trust"] = trust

    # Delete the source keys — the v3 trust block is the canonical home.
    envelope.pop("trust_score", None)
    envelope.pop("trust_decision", None)


def _inject_relationship_status(envelope: dict[str, Any]) -> None:
    """Transform 2 — relationship status + discovered_by injection (Decision 3).

    Mutates ``envelope`` in place. Detects v1 bare-array shape and converts
    to v3 object shape ``{"relationships": [...]}``. Then for every entry
    in the array, sets ``status`` and ``discovered_by`` defaults if missing.

    Existing values are not overwritten.
    """
    rels = envelope.get("relationships")

    # v1 shape: bare list at top level. Convert to v3 object.
    if isinstance(rels, list):
        envelope["relationships"] = {"relationships": rels}
        rels_block = envelope["relationships"]
    elif isinstance(rels, dict):
        rels_block = rels
    else:
        # Missing or wrong type — leave alone. The projector / validator
        # will surface that as a structural problem.
        return

    entries = rels_block.get("relationships")
    if not isinstance(entries, list):
        return

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        # v1 used `source_document_id` / `target_document_id`; v3 renamed to
        # `source_document_ref` / `target_document_ref`. Migrate the field
        # names without overwriting an existing v3-shaped value.
        if "source_document_ref" not in entry and "source_document_id" in entry:
            entry["source_document_ref"] = entry.pop("source_document_id")
        if "target_document_ref" not in entry and "target_document_id" in entry:
            entry["target_document_ref"] = entry.pop("target_document_id")
        if not entry.get("status"):
            entry["status"] = "confirmed"
        if not entry.get("discovered_by"):
            entry["discovered_by"] = "v1_migration"


def _promote_halobridge_blocks(envelope: dict[str, Any]) -> None:
    """Transform 3 — Q5 fix: promote v1.2–v1.6 blocks to top level.

    Mutates ``envelope`` in place. For each name in
    ``V12_V16_COMPLIANCE_BLOCKS`` (13 names — NOT federation):

    - If ``extensions.halobridge.<name>`` exists:
      - If top-level ``<name>`` exists, keep top-level + delete extensions
        copy (canonical home wins; the two are usually identical content
        from the double-emission bug).
      - Else copy extensions content to top level + delete extensions copy.

    If ``extensions.halobridge`` ends up empty, drop the ``halobridge``
    key. If ``extensions`` is empty, leave it as an empty dict (the v3
    schema requires ``extensions`` to be present at top level).
    """
    extensions = envelope.get("extensions")
    if not isinstance(extensions, dict):
        return
    halobridge = extensions.get("halobridge")
    if not isinstance(halobridge, dict):
        return

    for name in V12_V16_COMPLIANCE_BLOCKS:
        if name not in halobridge:
            continue
        ext_value = halobridge[name]
        if name in envelope:
            # Top-level wins (double-emission bug — both copies typically
            # carry identical content; the spec puts the canonical home at
            # top level).
            halobridge.pop(name, None)
        else:
            envelope[name] = ext_value
            halobridge.pop(name, None)

    # Clean up empty halobridge namespace.
    if not halobridge:
        extensions.pop("halobridge", None)
    # Do NOT delete the `extensions` key itself — the v3 schema requires
    # it at top level. An empty dict is fine.


def migrate_v1_to_v3(envelope: Any) -> dict[str, Any]:
    """Apply the three v1 -> v3 transforms.

    Returns a fresh dict — does not mutate the input. The result always
    has ``schema_version == "gallodoc-core/v3"``. Idempotent. Never
    raises — already-v3 envelopes pass through.

    See ``docs/specs/gallodoc-core-v3-reference-projector.md`` for the
    full contract.
    """
    if not isinstance(envelope, dict):
        return {"schema_version": "gallodoc-core/v3"}

    out: dict[str, Any] = copy.deepcopy(envelope)

    # Transform 1: flat trust merge. This also drains
    # `extensions.halobridge.trust_decision` as a source — `trust_decision`
    # is one of the v1.2–v1.6 blocks AND is the v1.5 source for the flat
    # trust merge. The merge consumes whichever copy is present (top-level
    # wins on conflict) and removes both, so Transform 3 has nothing left
    # to promote for `trust_decision`.
    _merge_flat_trust(out)

    # Transform 2: relationship status + discovered_by injection.
    _inject_relationship_status(out)

    # Transform 3: Q5 fix — promote remaining halobridge blocks.
    _promote_halobridge_blocks(out)

    # Always tag v3 at the end.
    out["schema_version"] = "gallodoc-core/v3"

    return out


__all__ = ["migrate_v1_to_v3"]
