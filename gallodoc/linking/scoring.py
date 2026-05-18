"""Signal extraction and confidence scoring for the deterministic linker.

Per Decision 3 (linker writes into ``relationships`` with
``status: "suggested"`` and ``discovered_by: "gallodoc-linker/3.0.0"``)
and Decision 5 (``::semantic_intent`` block resolves to
``gallounits.units[].semantic_intent`` — read here at weight 0.60).

The linker is deterministic: hash + ID matching plus a weighted sum.
No ML. The full signal catalog and weight rationale live in
``docs/specs/gallodoc-core-v3-linker.md`` §3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Weight table per docs/specs/gallodoc-core-v3-linker.md §3 and Decision 5.
# Tune at the table here.
SIGNAL_WEIGHTS: dict[str, float] = {
    "text_hash_match":             0.95,
    "claim_id_match":              0.85,
    "projection_hash_match":       0.70,
    "shared_evidence_ref":         0.60,   # per shared ref, capped
    "semantic_intent_match":       0.60,   # Decision 5
    "source_record_id_match":     0.50,
    "relationship_evidence_match": 0.40,
    "semantic_role_overlap":       0.10,
}

SHARED_EVIDENCE_REF_CAP: int = 3   # don't let one envelope dominate via many shared refs


@dataclass
class Signal:
    """A single matching signal between source and candidate."""

    name: str
    weight: float
    source_locator: str       # opaque locator string for evidence
    candidate_locator: str
    match_value_hash: str | None = None   # hash of the matched value, never raw


@dataclass
class ScoredCandidate:
    """A candidate envelope scored against the source."""

    source_document_id: str
    candidate_document_id: str
    signals: list[Signal] = field(default_factory=list)
    confidence: float = 0.0

    def add_signal(self, sig: Signal) -> None:
        self.signals.append(sig)
        self._recompute_confidence()

    def _recompute_confidence(self) -> None:
        total = 0.0
        shared_evidence_count = 0
        for s in self.signals:
            if s.name == "shared_evidence_ref":
                if shared_evidence_count >= SHARED_EVIDENCE_REF_CAP:
                    continue
                shared_evidence_count += 1
            total += s.weight
        self.confidence = min(1.0, total)


def extract_signals(source: dict[str, Any], candidate: dict[str, Any]) -> list[Signal]:
    """Extract all matching signals between source and candidate envelopes.

    Reads only hashes, IDs, and short vocabulary strings — never raw text.
    Locators are opaque strings that name the field path, not the value.
    """
    signals: list[Signal] = []

    # 1. text_hash matches on gallounits.units[]
    src_units = ((source.get("gallounits") or {}).get("units") or [])
    cand_units = ((candidate.get("gallounits") or {}).get("units") or [])
    src_hashes: dict[str, dict[str, Any]] = {}
    for u in src_units:
        if isinstance(u, dict) and u.get("text_hash"):
            src_hashes[u["text_hash"]] = u
    cand_hashes: dict[str, dict[str, Any]] = {}
    for u in cand_units:
        if isinstance(u, dict) and u.get("text_hash"):
            cand_hashes[u["text_hash"]] = u
    for h in sorted(set(src_hashes) & set(cand_hashes)):
        signals.append(Signal(
            name="text_hash_match",
            weight=SIGNAL_WEIGHTS["text_hash_match"],
            source_locator=f"gallounits.units[unit_id={src_hashes[h].get('unit_id', '?')}].text_hash",
            candidate_locator=f"gallounits.units[unit_id={cand_hashes[h].get('unit_id', '?')}].text_hash",
            match_value_hash=h,
        ))

    # 2. truth_ledger.claims[].claim_id matches
    src_claims = ((source.get("truth_ledger") or {}).get("claims") or [])
    cand_claims = ((candidate.get("truth_ledger") or {}).get("claims") or [])
    src_claim_ids = {c.get("claim_id") for c in src_claims if isinstance(c, dict) and c.get("claim_id")}
    cand_claim_ids = {c.get("claim_id") for c in cand_claims if isinstance(c, dict) and c.get("claim_id")}
    for cid in sorted(src_claim_ids & cand_claim_ids):
        signals.append(Signal(
            name="claim_id_match",
            weight=SIGNAL_WEIGHTS["claim_id_match"],
            source_locator=f"truth_ledger.claims[claim_id={cid}]",
            candidate_locator=f"truth_ledger.claims[claim_id={cid}]",
            match_value_hash=None,
        ))

    # 3. projection_hash matches on gallounits.model_projections[]
    src_projs = ((source.get("gallounits") or {}).get("model_projections") or [])
    cand_projs = ((candidate.get("gallounits") or {}).get("model_projections") or [])
    src_proj_hashes: dict[str, dict[str, Any]] = {}
    for p in src_projs:
        if isinstance(p, dict) and p.get("projection_hash"):
            src_proj_hashes[p["projection_hash"]] = p
    cand_proj_hashes: dict[str, dict[str, Any]] = {}
    for p in cand_projs:
        if isinstance(p, dict) and p.get("projection_hash"):
            cand_proj_hashes[p["projection_hash"]] = p
    for h in sorted(set(src_proj_hashes) & set(cand_proj_hashes)):
        signals.append(Signal(
            name="projection_hash_match",
            weight=SIGNAL_WEIGHTS["projection_hash_match"],
            source_locator=f"gallounits.model_projections[projection_id={src_proj_hashes[h].get('projection_id', '?')}]",
            candidate_locator=f"gallounits.model_projections[projection_id={cand_proj_hashes[h].get('projection_id', '?')}]",
            match_value_hash=h,
        ))

    # 4. Shared evidence_refs across truth_ledger.claims[]
    src_evidence: set[str] = set()
    for c in src_claims:
        if isinstance(c, dict):
            for ref in (c.get("evidence_refs") or []):
                if isinstance(ref, str):
                    src_evidence.add(ref)
    cand_evidence: set[str] = set()
    for c in cand_claims:
        if isinstance(c, dict):
            for ref in (c.get("evidence_refs") or []):
                if isinstance(ref, str):
                    cand_evidence.add(ref)
    for ref in sorted(src_evidence & cand_evidence):
        signals.append(Signal(
            name="shared_evidence_ref",
            weight=SIGNAL_WEIGHTS["shared_evidence_ref"],
            source_locator=f"truth_ledger.claims[].evidence_refs[ref={ref}]",
            candidate_locator=f"truth_ledger.claims[].evidence_refs[ref={ref}]",
            match_value_hash=None,
        ))

    # 5. semantic_intent matches (Decision 5)
    src_intents = {u.get("semantic_intent") for u in src_units if isinstance(u, dict) and u.get("semantic_intent")}
    cand_intents = {u.get("semantic_intent") for u in cand_units if isinstance(u, dict) and u.get("semantic_intent")}
    for intent in sorted(src_intents & cand_intents):
        signals.append(Signal(
            name="semantic_intent_match",
            weight=SIGNAL_WEIGHTS["semantic_intent_match"],
            source_locator=f"gallounits.units[].semantic_intent={intent}",
            candidate_locator=f"gallounits.units[].semantic_intent={intent}",
            match_value_hash=None,
        ))

    # 6. source.source_record_id (hash if available)
    src_source = source.get("source") or {}
    cand_source = candidate.get("source") or {}
    src_rid = src_source.get("source_record_id_hash") or src_source.get("source_record_id")
    cand_rid = cand_source.get("source_record_id_hash") or cand_source.get("source_record_id")
    if src_rid and cand_rid and src_rid == cand_rid:
        signals.append(Signal(
            name="source_record_id_match",
            weight=SIGNAL_WEIGHTS["source_record_id_match"],
            source_locator="source.source_record_id",
            candidate_locator="source.source_record_id",
            match_value_hash=src_rid if isinstance(src_rid, str) and src_rid.startswith("sha256:") else None,
        ))

    # 7. relationships.relationship_evidence[].value_hash matches
    src_rels_block = source.get("relationships") or {}
    cand_rels_block = candidate.get("relationships") or {}
    src_rels = (src_rels_block.get("relationships") or []) if isinstance(src_rels_block, dict) else []
    cand_rels = (cand_rels_block.get("relationships") or []) if isinstance(cand_rels_block, dict) else []
    src_evi_block = (src_rels_block.get("relationship_evidence") or []) if isinstance(src_rels_block, dict) else []
    cand_evi_block = (cand_rels_block.get("relationship_evidence") or []) if isinstance(cand_rels_block, dict) else []
    src_evi_hashes: set[str] = set()
    for r in src_rels:
        if isinstance(r, dict):
            for ev in (r.get("relationship_evidence") or []):
                if isinstance(ev, dict) and ev.get("value_hash"):
                    src_evi_hashes.add(ev["value_hash"])
    for ev in src_evi_block:
        if isinstance(ev, dict) and ev.get("value_hash"):
            src_evi_hashes.add(ev["value_hash"])
    cand_evi_hashes: set[str] = set()
    for r in cand_rels:
        if isinstance(r, dict):
            for ev in (r.get("relationship_evidence") or []):
                if isinstance(ev, dict) and ev.get("value_hash"):
                    cand_evi_hashes.add(ev["value_hash"])
    for ev in cand_evi_block:
        if isinstance(ev, dict) and ev.get("value_hash"):
            cand_evi_hashes.add(ev["value_hash"])
    for h in sorted(src_evi_hashes & cand_evi_hashes):
        signals.append(Signal(
            name="relationship_evidence_match",
            weight=SIGNAL_WEIGHTS["relationship_evidence_match"],
            source_locator=f"relationships.relationship_evidence[value_hash={h}]",
            candidate_locator=f"relationships.relationship_evidence[value_hash={h}]",
            match_value_hash=h,
        ))

    # 8. semantic_role overlap (weak tie-breaker)
    src_roles = {u.get("semantic_role") for u in src_units if isinstance(u, dict) and u.get("semantic_role")}
    cand_roles = {u.get("semantic_role") for u in cand_units if isinstance(u, dict) and u.get("semantic_role")}
    for role in sorted(src_roles & cand_roles):
        signals.append(Signal(
            name="semantic_role_overlap",
            weight=SIGNAL_WEIGHTS["semantic_role_overlap"],
            source_locator=f"gallounits.units[].semantic_role={role}",
            candidate_locator=f"gallounits.units[].semantic_role={role}",
            match_value_hash=None,
        ))

    return signals


def score(source: dict[str, Any], candidate: dict[str, Any]) -> ScoredCandidate:
    """Score a candidate against a source. Returns a ScoredCandidate with all signals."""
    src_id = (source.get("identity") or {}).get("gallodoc_id") or "(unknown_source)"
    cand_id = (candidate.get("identity") or {}).get("gallodoc_id") or "(unknown_candidate)"
    scored = ScoredCandidate(source_document_id=src_id, candidate_document_id=cand_id)
    for sig in extract_signals(source, candidate):
        scored.add_signal(sig)
    return scored


__all__ = [
    "SIGNAL_WEIGHTS",
    "SHARED_EVIDENCE_REF_CAP",
    "Signal",
    "ScoredCandidate",
    "extract_signals",
    "score",
]
