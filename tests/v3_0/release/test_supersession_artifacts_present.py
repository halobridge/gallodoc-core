"""Verify the three Decision 1 supersession artifacts are present in the tree.

These are checked separately from the release safety gate itself so the
test signal stays cheap and the failure mode points directly at the
missing artifact.
"""

from __future__ import annotations

import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# Match the same set the release safety gate enforces.
_V3_FROZEN_SELF_DESCRIPTIONS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bv3\s+is\s+frozen\b",
        r"\bv3\.0\s+is\s+frozen\b",
        r"\bfrozen\s+v3\b",
        r"\bfrozen\s+v3\.0\b",
    )
)


def test_frozen_doc_preamble_present() -> None:
    """docs/GALLODOC_CORE_V1_FROZEN.md must carry the 'Superseded by v3' preamble
    within the first 30 lines."""
    path = PACKAGE_ROOT / "docs" / "GALLODOC_CORE_V1_FROZEN.md"
    assert path.is_file(), f"Missing: {path}"
    head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:30])
    assert "Superseded by v3" in head, (
        "docs/GALLODOC_CORE_V1_FROZEN.md must include 'Superseded by v3' in "
        "the first 30 lines (Decision 1 supersession move #1)."
    )


def test_pyproject_classifier_bumped() -> None:
    """pyproject.toml must carry the 'Development Status :: 4 - Beta' classifier."""
    path = PACKAGE_ROOT / "pyproject.toml"
    assert path.is_file(), f"Missing: {path}"
    text = path.read_text(encoding="utf-8")
    assert '"Development Status :: 4 - Beta"' in text, (
        "pyproject.toml must carry 'Development Status :: 4 - Beta' "
        "(Decision 1 supersession move #2)."
    )


def test_frozen_framing_dropped_from_release_notes() -> None:
    """RELEASE_NOTES_3.0.0.md must NOT self-describe v3 as frozen."""
    path = PACKAGE_ROOT / "RELEASE_NOTES_3.0.0.md"
    assert path.is_file(), f"Missing: {path}"
    text = path.read_text(encoding="utf-8")
    hits = [p.pattern for p in _V3_FROZEN_SELF_DESCRIPTIONS if p.search(text)]
    assert not hits, (
        "RELEASE_NOTES_3.0.0.md self-describes v3 as 'frozen' (matched: "
        f"{hits}). Decision 1 supersession move #3 requires concrete "
        "stability commitments instead."
    )
