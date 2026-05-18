"""GalloDoc Units engine — deterministic, local-only, cryptographically stable.

> Models may tokenize differently, but they should all be able to point back
> to the same GalloUnit.

Public API:

* :func:`normalize_text` — Unicode-NFC + whitespace normalization.
* :func:`compute_text_hash` — sha256 over normalized text.
* :func:`segment_text_to_units` — cut text into ordered GalloUnits.
* :func:`build_gallounits_block` — full ``gallounits`` block ready to drop
  into a GalloDoc envelope.
* :class:`gallodoc.units.classifier.UnitClassifier` — rule-based unit type +
  semantic-role classifier.
* :func:`gallodoc.units.projections.estimate_tokens_for_unit` /
  :func:`gallodoc.units.projections.build_model_projection` — token / model
  projections.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Iterable

from gallodoc.units.classifier import UnitClassifier, classify_unit
from gallodoc.units.projections import (
    build_model_projection,
    estimate_tokens_for_unit,
)

UNIT_STRATEGY_V1 = "gallounit_v1"

# Order matters — longer/more specific first.
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT = re.compile(r"(?<=[\.\?!])\s+(?=[A-Z(\"'])")


def normalize_text(text: str) -> str:
    """Return canonical text suitable for hashing.

    * NFC normalization,
    * line-ending normalization,
    * trim leading/trailing whitespace per line,
    * collapse runs of in-line whitespace to a single space,
    * trim outer whitespace.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out_lines: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        line = re.sub(r"[ \t]+", " ", line)
        out_lines.append(line)
    return "\n".join(out_lines).strip()


def compute_text_hash(text: str) -> str:
    """sha256 of ``normalize_text(text)``, prefixed ``sha256:``."""
    digest = hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _short_summary(text: str, *, limit: int = 240) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _gen_unit_id(prefix: str, idx: int, *, unique_seed: str = "") -> str:
    if unique_seed:
        # Suffix the index with a 6-char fingerprint so unit_ids stay unique
        # even when multiple documents share the same heading text.
        fp = hashlib.sha256(unique_seed.encode("utf-8")).hexdigest()[:6]
        return f"{prefix}_{idx:04d}_{fp}"
    return f"{prefix}_{idx:04d}"


def segment_text_to_units(
    text: str,
    *,
    strategy: str = UNIT_STRATEGY_V1,
    classify: bool = True,
) -> list[dict[str, Any]]:
    """Cut ``text`` into ordered GalloUnits.

    ``strategy`` is reserved for future strategies; v1 only ships
    ``gallounit_v1``.

    Returns a list of unit dicts that conform to the open-core
    ``gallounits.units[]`` shape. Source spans use character offsets within
    the *original* (unnormalized) text so verifiers can map back to the bytes
    they were given.
    """
    if strategy != UNIT_STRATEGY_V1:
        raise ValueError(f"unknown unit_strategy: {strategy!r}")

    if not text:
        return []

    units: list[dict[str, Any]] = []
    classifier = UnitClassifier() if classify else None
    seq = 0

    cursor = 0
    for paragraph in _PARAGRAPH_SPLIT.split(text):
        if not paragraph.strip():
            cursor += len(paragraph) + 2  # account for the split delimiter
            continue
        # Find this paragraph's offset in the original text.
        start = text.find(paragraph, cursor)
        if start == -1:
            start = cursor
        end = start + len(paragraph)
        cursor = end

        # Decide whether to emit one paragraph unit or split into sentences.
        sentences = [s for s in _SENTENCE_SPLIT.split(paragraph) if s.strip()]
        if len(sentences) <= 1 or len(paragraph) < 240:
            seq += 1
            unit = _build_unit(
                seq=seq,
                paragraph=paragraph,
                source=text,
                start=start,
                end=end,
                unit_type_hint="paragraph",
            )
            if classifier is not None:
                cls = classifier.classify(paragraph)
                unit["unit_type"] = cls["unit_type"]
                unit["semantic_role"] = cls["semantic_role"]
                unit["confidence"] = cls["confidence"]
            units.append(unit)
            continue

        # Sentence-level split inside the paragraph.
        offset = start
        for sentence in sentences:
            sentence_start = text.find(sentence, offset)
            if sentence_start == -1:
                sentence_start = offset
            sentence_end = sentence_start + len(sentence)
            offset = sentence_end
            seq += 1
            unit = _build_unit(
                seq=seq,
                paragraph=sentence,
                source=text,
                start=sentence_start,
                end=sentence_end,
                unit_type_hint="sentence",
            )
            if classifier is not None:
                cls = classifier.classify(sentence)
                unit["unit_type"] = cls["unit_type"]
                unit["semantic_role"] = cls["semantic_role"]
                unit["confidence"] = cls["confidence"]
            units.append(unit)

    return units


def _build_unit(
    *,
    seq: int,
    paragraph: str,
    source: str,
    start: int,
    end: int,
    unit_type_hint: str,
) -> dict[str, Any]:
    """Build a single GalloUnit dict (pre-classifier)."""
    text_hash = compute_text_hash(paragraph)
    unit_id = _gen_unit_id("gu", seq, unique_seed=text_hash)
    return {
        "unit_id": unit_id,
        "unit_type": unit_type_hint,
        "semantic_role": "unknown",
        "source_span": {
            "page": None,
            "start_char": start,
            "end_char": end,
            "start_time_ms": None,
            "end_time_ms": None,
            "region": None,
        },
        "text_hash": text_hash,
        "content_summary": _short_summary(paragraph),
        "confidence": 0.6,
        "evidence_refs": [],
        "relationship_refs": [],
        "extractions": {},
        "validation_refs": [],
        "ai_usage_refs": [],
    }


def build_gallounits_block(
    text: str,
    *,
    strategy: str = UNIT_STRATEGY_V1,
    classify: bool = True,
) -> dict[str, Any]:
    """Build the ``gallounits`` envelope block for ``text``.

    Returns a dict suitable for direct insertion into a GalloDoc envelope:

    .. code-block:: python

        envelope["gallounits"] = build_gallounits_block(canonical_text)
    """
    units = segment_text_to_units(text, strategy=strategy, classify=classify)
    return {
        "unit_strategy": strategy,
        "canonical_text_hash": compute_text_hash(text or ""),
        "units": units,
        "model_projections": [],
    }


__all__ = [
    "UNIT_STRATEGY_V1",
    "normalize_text",
    "compute_text_hash",
    "segment_text_to_units",
    "build_gallounits_block",
    "UnitClassifier",
    "classify_unit",
    "build_model_projection",
    "estimate_tokens_for_unit",
]
