"""Lightweight regex-based artifact extractor.

Each artifact is linked to a GalloUnit via ``source_unit_id`` so consumers can
trace provenance back to a stable unit. The extractor is deliberately
**conservative**: it does not attempt to parse semantics, currency precision,
locale-specific dates, or noise-resistant phone numbers. The results are
labeled ``needs_review=True`` whenever the rule has known limitations, and
the ``method`` field always reads ``"regex_v1"`` so downstream consumers can
tell that this is the open-core baseline rather than a HaloBridge enterprise
extractor.

Artifact types:

* ``date``
* ``amount``
* ``email``
* ``phone``
* ``reference_id``
* ``heading``
* ``payment_terms``
* ``signature_block``
* ``table_row``
* ``line_item_candidate``
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

ARTIFACT_TYPES = (
    "date",
    "amount",
    "email",
    "phone",
    "reference_id",
    "heading",
    "payment_terms",
    "signature_block",
    "table_row",
    "line_item_candidate",
)

_RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_RE_PHONE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}(?!\d)"
)
_RE_DATE_NUM = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_RE_DATE_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_RE_DATE_TEXT = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
_RE_AMOUNT = re.compile(
    r"(?:\$|€|£|USD|EUR|GBP)\s?\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?\b|\b\d+(?:\.\d{2})\s*(?:USD|EUR|GBP|dollars|euros|pounds)\b",
    re.IGNORECASE,
)
_RE_REFERENCE_ID = re.compile(
    r"\b(?:invoice|inv|po|p\.o\.|order|ref|reference|claim|case|account|acct|ticket|tracking)\s*[#:\-]?\s*([A-Z0-9][A-Z0-9\-_/]{3,32})\b",
    re.IGNORECASE,
)
_RE_HEADING = re.compile(r"^([A-Z][A-Z0-9 \-_/]{2,80})$|^([0-9]+(?:\.[0-9]+)*\s+[A-Z].{0,80})$")
_RE_PAYMENT_TERMS = re.compile(
    r"\b(net\s*\d+\s*days?|payment\s*terms?\s*[:\-]?\s*[^.\n]{0,80}|due\s*on\s*receipt|invoice\s*due|payable\s*within\s*\d+\s*days?)\b",
    re.IGNORECASE,
)
_RE_SIGNATURE = re.compile(
    r"(?i)\b(signature(?:\s*line)?|signed\s*by|by\s*:\s*_+|date\s*:\s*_+|x\s*_+|/s/\s*[A-Z][A-Za-z\-' ]{1,40})\b"
)
_RE_TABLE_ROW = re.compile(r".+(?:\s*\|\s*.+){2,}|.+(?:\s*\t\s*.+){2,}")
_RE_LINE_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[\.\)])\s+\S")


def _aid(unit_id: str, artifact_type: str, value: str, idx: int) -> str:
    seed = f"{unit_id}|{artifact_type}|{value}|{idx}".encode("utf-8")
    return f"art_{hashlib.sha256(seed).hexdigest()[:12]}"


def _make_artifact(
    *,
    unit_id: str,
    artifact_type: str,
    value: str,
    idx: int,
    confidence: float,
    needs_review: bool,
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_id": _aid(unit_id, artifact_type, value, idx),
        "artifact_type": artifact_type,
        "source_unit_id": unit_id,
        "fields": dict(fields or {}),
        "value_summary": value[:240],
        "confidence": round(float(confidence), 3),
        "method": "regex_v1",
        "needs_review": bool(needs_review),
    }


def extract_basic_artifacts(units: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract artifacts from a list of GalloUnits.

    Returns a flat list of artifact dicts. Order matches the input units, then
    artifact discovery order within each unit.
    """
    out: list[dict[str, Any]] = []
    for unit in units or []:
        if not isinstance(unit, dict):
            continue
        unit_id = str(unit.get("unit_id", ""))
        text = str(unit.get("content_summary") or unit.get("text") or "")
        if not text:
            continue

        idx = 0
        # Headings — only when classifier already labelled it as heading.
        if unit.get("unit_type") == "heading" or _RE_HEADING.match(text):
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="heading", value=text, idx=idx,
                confidence=0.85, needs_review=False,
                fields={"raw": text},
            ))
            idx += 1

        # Payment terms.
        for m in _RE_PAYMENT_TERMS.finditer(text):
            value = m.group(0).strip()
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="payment_terms", value=value, idx=idx,
                confidence=0.85, needs_review=True,
                fields={"raw": value},
            ))
            idx += 1

        # Signature blocks.
        if _RE_SIGNATURE.search(text):
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="signature_block", value=text[:200], idx=idx,
                confidence=0.75, needs_review=True,
            ))
            idx += 1

        # Table rows / line-item candidates.
        if _RE_TABLE_ROW.match(text):
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="table_row", value=text[:200], idx=idx,
                confidence=0.7, needs_review=True,
            ))
            idx += 1
        elif _RE_LINE_ITEM.match(text):
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="line_item_candidate", value=text[:200], idx=idx,
                confidence=0.6, needs_review=True,
            ))
            idx += 1

        # Dates.
        for pat, label in ((_RE_DATE_ISO, "iso"), (_RE_DATE_NUM, "numeric"), (_RE_DATE_TEXT, "text")):
            for m in pat.finditer(text):
                out.append(_make_artifact(
                    unit_id=unit_id, artifact_type="date", value=m.group(0), idx=idx,
                    confidence=0.85 if label == "iso" else 0.7,
                    needs_review=label != "iso",
                    fields={"format": label},
                ))
                idx += 1

        # Amounts.
        for m in _RE_AMOUNT.finditer(text):
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="amount", value=m.group(0).strip(), idx=idx,
                confidence=0.8, needs_review=True,
                fields={"raw": m.group(0)},
            ))
            idx += 1

        # Emails.
        for m in _RE_EMAIL.finditer(text):
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="email", value=m.group(0), idx=idx,
                confidence=0.95, needs_review=False,
            ))
            idx += 1

        # Phones.
        for m in _RE_PHONE.finditer(text):
            value = m.group(0).strip()
            digits = sum(1 for c in value if c.isdigit())
            if digits < 7:
                continue
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="phone", value=value, idx=idx,
                confidence=0.6, needs_review=True,
                fields={"digits": digits},
            ))
            idx += 1

        # Reference IDs.
        for m in _RE_REFERENCE_ID.finditer(text):
            out.append(_make_artifact(
                unit_id=unit_id, artifact_type="reference_id", value=m.group(0).strip(), idx=idx,
                confidence=0.7, needs_review=True,
                fields={"id": m.group(1)},
            ))
            idx += 1

    return out


__all__ = ["ARTIFACT_TYPES", "extract_basic_artifacts"]
