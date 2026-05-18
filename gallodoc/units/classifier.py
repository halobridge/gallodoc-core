"""Tiny rule-based GalloUnit classifier.

Identifies unit type and semantic role from short text fragments without any
external dependencies. Optional scikit-learn / ONNX backends can hook into
:meth:`UnitClassifier.classify_with_model` later; if no optional backend is
installed, the classifier falls back to the rules.

Classification labels (unit type):

* heading
* paragraph
* clause
* table_row
* line_item
* signature_block
* payment_terms
* amount_block
* date_block
* unknown

A confidence score (0.0-1.0) is always reported. Rule matches anchor at
0.85; the fallback paragraph label sits at 0.5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_RE_HEADING = re.compile(r"^([A-Z][A-Z0-9 \-_/]{2,80}|[0-9]+(\.[0-9]+)*\s+[A-Z].{0,80})$", re.MULTILINE)
_RE_TABLE_ROW = re.compile(r"^[^\n]*\|[^\n]*\|[^\n]*$|^[^\n]*\t[^\n]*\t[^\n]*$")
_RE_LINE_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[\.\)])\s+\S")
_RE_SIGNATURE = re.compile(r"\b(signature|signed by|by\s*:\s*_+|date\s*:\s*_+|\bx_+)\b", re.IGNORECASE)
_RE_PAYMENT_TERMS = re.compile(r"\b(net\s*\d+\s*days?|payment\s*terms?|due\s*on\s*receipt|invoice\s*due|payable\s*within)\b", re.IGNORECASE)
_RE_AMOUNT = re.compile(r"(?:\$|USD|EUR|GBP)\s?\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?\b|\b\d+(?:\.\d{2})\s*(?:USD|EUR|GBP|dollars)\b", re.IGNORECASE)
_RE_DATE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4})\b", re.IGNORECASE)
_RE_CLAUSE = re.compile(r"\b(shall|hereby|notwithstanding|in\s*the\s*event|provided\s*that|subject\s*to|warrants?|represents?|agrees?\s*to)\b", re.IGNORECASE)


SEMANTIC_ROLE_HINTS: dict[str, str] = {
    "payment_terms": "payment_terms",
    "amount_block": "amount",
    "date_block": "date",
    "signature_block": "signature",
    "line_item": "line_item",
    "table_row": "table_row",
    "heading": "section_label",
    "clause": "legal_clause",
    "paragraph": "narrative",
    "unknown": "unknown",
}


@dataclass
class UnitClassifier:
    """Rule-first unit classifier.

    Optional backends (sklearn, ONNX) can be wired by overriding
    :meth:`classify_with_model`. The default implementation always returns
    ``None`` so :meth:`classify` falls back to the rules.
    """

    use_optional_backend: bool = True

    def classify(self, text: str) -> dict[str, Any]:
        """Return ``{"unit_type", "semantic_role", "confidence"}`` for ``text``."""
        text = (text or "").strip()
        if not text:
            return self._result("unknown", 0.0)

        if self.use_optional_backend:
            backend = self.classify_with_model(text)
            if backend is not None:
                return backend

        return self._classify_rules(text)

    def classify_with_model(self, text: str) -> dict[str, Any] | None:
        """Optional backend hook. Default: no backend installed → ``None``."""
        return None

    # ---------------------------------------------------------------- rules

    def _classify_rules(self, text: str) -> dict[str, Any]:
        # Most specific patterns first.
        if _RE_PAYMENT_TERMS.search(text):
            return self._result("payment_terms", 0.92)
        if _RE_SIGNATURE.search(text):
            return self._result("signature_block", 0.9)
        if _RE_TABLE_ROW.match(text):
            return self._result("table_row", 0.88)
        if _RE_LINE_ITEM.match(text):
            return self._result("line_item", 0.85)
        if _RE_AMOUNT.search(text) and len(text) <= 200:
            return self._result("amount_block", 0.82)
        if _RE_DATE.search(text) and len(text) <= 120:
            return self._result("date_block", 0.8)
        if _RE_HEADING.match(text):
            return self._result("heading", 0.85)
        if _RE_CLAUSE.search(text):
            return self._result("clause", 0.7)
        return self._result("paragraph", 0.5)

    @staticmethod
    def _result(unit_type: str, confidence: float) -> dict[str, Any]:
        return {
            "unit_type": unit_type,
            "semantic_role": SEMANTIC_ROLE_HINTS.get(unit_type, "unknown"),
            "confidence": round(confidence, 3),
        }


def classify_unit(text: str) -> dict[str, Any]:
    """Convenience wrapper around :class:`UnitClassifier`."""
    return UnitClassifier().classify(text)


__all__ = ["UnitClassifier", "classify_unit", "SEMANTIC_ROLE_HINTS"]
