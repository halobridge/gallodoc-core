"""GalloDoc deterministic linker — proposes relationships between v3 envelopes.

Decision 3: linker output writes into ``relationships`` with
``status: "suggested"`` and ``discovered_by: "gallodoc-linker/3.0.0"``.
Decision 5: ``::semantic_intent`` GalloMarkdown blocks resolve to
``gallounits.units[].semantic_intent`` and are read here as a signal.

Spec: ``docs/specs/gallodoc-core-v3-linker.md`` +
``docs/specs/gallodoc-semantic-intent-v3.md``.
"""

from __future__ import annotations

from gallodoc.linking.evidence import SIGNAL_TO_EVIDENCE_TYPE, build_evidence
from gallodoc.linking.linker import (
    LINKER_DISCOVERED_BY,
    LinkerOutput,
    RelationshipCandidate,
    apply_relationship_decision,
    link,
    write_into_envelope,
)
from gallodoc.linking.rules import (
    ALLOWED_RELATIONSHIP_TYPES,
    SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE,
    classify,
)
from gallodoc.linking.scoring import (
    SHARED_EVIDENCE_REF_CAP,
    SIGNAL_WEIGHTS,
    ScoredCandidate,
    Signal,
    extract_signals,
    score,
)

__all__ = [
    "ALLOWED_RELATIONSHIP_TYPES",
    "LINKER_DISCOVERED_BY",
    "LinkerOutput",
    "RelationshipCandidate",
    "SEMANTIC_INTENT_TO_RELATIONSHIP_TYPE",
    "SHARED_EVIDENCE_REF_CAP",
    "SIGNAL_TO_EVIDENCE_TYPE",
    "SIGNAL_WEIGHTS",
    "ScoredCandidate",
    "Signal",
    "apply_relationship_decision",
    "build_evidence",
    "classify",
    "extract_signals",
    "link",
    "score",
    "write_into_envelope",
]
