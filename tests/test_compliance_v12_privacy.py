"""Privacy-oriented checks for GalloDoc Core v1.2 compliance examples."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_V12 = PACKAGE_ROOT / "examples" / "v1_2" / "gallodoc_consent_custody_attestation.json"

_URL = re.compile(r"(?i)https?://")
_SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
_BAD_EMAIL = re.compile(r"\b[\w.+-]+@(?!example\.com\b|halobridge\.ai\b)[\w.-]+\.[a-z]{2,}\b", re.I)


@pytest.mark.skipif(not EXAMPLE_V12.is_file(), reason="missing v1.2 example")
def test_v12_example_text_has_no_urls_ssn_or_disallowed_emails():
    text = EXAMPLE_V12.read_text(encoding="utf-8")
    assert not _URL.search(text), "example must not contain raw http(s) URLs"
    assert not _SSN.search(text), "example must not contain SSN-shaped literals"
    assert not _BAD_EMAIL.search(text), "example must use example.com / halobridge.ai emails only"
