"""v3 envelope must carry all 18 required top-level sections.

Removing any one section trips "required field missing" mentioning that
section. v3's single addition over v1 is the consolidated ``trust`` block.
"""

from __future__ import annotations

import pytest

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


_V3_REQUIRED = (
    "schema_version",
    "identity",
    "source",
    "purpose",
    "lifecycle",
    "activity",
    "relationships",
    "evidence",
    "validations",
    "security",
    "exports",
    "extensions",
    "ai_usage",
    "gallounits",
    "certification",
    "gstp",
    "truth_ledger",
    "trust",
)


def test_minimal_v3_envelope_validates() -> None:
    env = minimal_v3_envelope()
    result = validate_envelope(env)
    assert result.valid, f"minimal v3 envelope must validate: {[(i.path, i.message) for i in result.errors()][:8]}"


def test_v3_has_18_required_sections() -> None:
    assert len(_V3_REQUIRED) == 18


@pytest.mark.parametrize("section", _V3_REQUIRED)
def test_removing_any_required_section_fails(section: str) -> None:
    env = minimal_v3_envelope()
    env.pop(section, None)
    result = validate_envelope(env)
    assert not result.valid, f"envelope without {section!r} must fail validation"
    if section == "schema_version":
        # Removing schema_version trips the dispatch's "unknown schema version"
        # branch first — that's the contract, and it counts as a structural
        # failure on the right path.
        assert any(
            i.path == "schema_version" and "unknown" in i.message.lower()
            for i in result.errors()
        )
    else:
        # Other missing required sections trip the structural validator's
        # "required field missing" check at that path.
        matching = [
            i
            for i in result.errors()
            if i.path == section and "required field missing" in i.message
        ]
        assert matching, (
            f"expected 'required field missing' at path={section!r}, "
            f"got {[(i.path, i.message) for i in result.errors()]}"
        )


def test_trust_is_the_18th_required_section() -> None:
    """v1 had 17 required; v3 adds `trust`. Removing `trust` alone fails."""
    env = minimal_v3_envelope()
    env.pop("trust")
    result = validate_envelope(env)
    assert not result.valid
    matching = [
        i for i in result.errors() if i.path == "trust" and "required field missing" in i.message
    ]
    assert matching
