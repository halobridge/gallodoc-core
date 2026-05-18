"""Tests for the ``::semantic_intent`` GalloMarkdown block (Decision 5).

The block routes to ``gallounits.units[].semantic_intent`` on the unit
named by ``unit_id``. The block is the canonical authoring surface for
relationship intent; the linker reads matching values as a signal.
"""

from __future__ import annotations

import pytest

from gallodoc.markdown import (
    SEMANTIC_INTENT_VOCABULARY,
    GalloMDError,
    gallomd_to_gallodoc,
)
from gallodoc.markdown_renderer import gallodoc_to_gallomd


def _gmd_with_intent(unit_id: str = "gu_017", intent: str = "invoice_to_employee_approver") -> str:
    return f"""::gallodoc
schema_version: gallodoc-core/v3
doc_id: doc_invoice_001
title: Invoice with intent
::

# Invoice

Some paragraph content here for the body.

::semantic_intent
unit_id: {unit_id}
intent: {intent}
::
"""


def test_semantic_intent_block_routes_to_unit() -> None:
    env = gallomd_to_gallodoc(_gmd_with_intent("gu_017", "invoice_to_employee_approver"))
    units = env["gallounits"]["units"]
    matches = [u for u in units if u.get("unit_id") == "gu_017"]
    assert matches, f"no unit with id gu_017 found in {units}"
    assert matches[0]["semantic_intent"] == "invoice_to_employee_approver"


def test_semantic_intent_block_attaches_to_existing_unit() -> None:
    """When unit_id matches a content-generated unit, attach in place."""
    gmd = """::gallodoc
schema_version: gallodoc-core/v3
doc_id: doc_a
::

# Heading

::semantic_intent
unit_id: u-h-0001
intent: contract_supersedes_contract
::
"""
    env = gallomd_to_gallodoc(gmd)
    units = env["gallounits"]["units"]
    h1 = [u for u in units if u.get("unit_id") == "u-h-0001"]
    assert h1, "expected heading unit u-h-0001 to exist"
    assert h1[0]["semantic_intent"] == "contract_supersedes_contract"
    # The intent did not create a duplicate unit
    assert sum(1 for u in units if u.get("unit_id") == "u-h-0001") == 1


def test_semantic_intent_block_round_trips() -> None:
    """Render → parse → render preserves the ::semantic_intent block."""
    src = _gmd_with_intent("gu_017", "invoice_to_employee_approver")
    env = gallomd_to_gallodoc(src)
    rendered = gallodoc_to_gallomd(env)
    # The block reappears in the rendered output
    assert "::semantic_intent" in rendered
    assert "invoice_to_employee_approver" in rendered
    # Round-trip: compile the rendered text again — the intent survives.
    env2 = gallomd_to_gallodoc(rendered)
    units2 = env2["gallounits"]["units"]
    assert any(u.get("semantic_intent") == "invoice_to_employee_approver" for u in units2)


def test_unknown_vocabulary_raises_gallomd_error() -> None:
    with pytest.raises(GalloMDError) as exc_info:
        gallomd_to_gallodoc(_gmd_with_intent("gu_x", "not_in_vocabulary"))
    msg = str(exc_info.value)
    assert "not_in_vocabulary" in msg
    assert "vocabulary" in msg.lower()


def test_missing_intent_field_raises_gallomd_error() -> None:
    gmd = """::gallodoc
schema_version: gallodoc-core/v3
doc_id: doc_x
::

# x

::semantic_intent
unit_id: gu_017
::
"""
    with pytest.raises(GalloMDError, match="intent"):
        gallomd_to_gallodoc(gmd)


def test_block_creates_minimal_unit_when_unit_id_unknown() -> None:
    """unit_id not present among content-derived units → create a placeholder."""
    gmd = """::gallodoc
schema_version: gallodoc-core/v3
doc_id: doc_y
::

# y

::semantic_intent
unit_id: gu_999_new
intent: claim_to_supporting_document
::
"""
    env = gallomd_to_gallodoc(gmd)
    units = env["gallounits"]["units"]
    new_units = [u for u in units if u.get("unit_id") == "gu_999_new"]
    assert new_units, "expected placeholder unit to be created"
    assert new_units[0]["semantic_intent"] == "claim_to_supporting_document"


def test_existing_block_types_still_work_alongside_semantic_intent() -> None:
    """Adding ::semantic_intent does not break the existing 7 block types."""
    gmd = """::gallodoc
schema_version: gallodoc-core/v3
doc_id: doc_full
title: Mixed blocks
::

# Header

Some text.

::artifact family=invoice id=art_1
total: 100
::

::evidence id=ev_1
source_ref: ref_1
hash: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
::

::semantic_intent
unit_id: u-h-0001
intent: invoice_to_employee_approver
::
"""
    env = gallomd_to_gallodoc(gmd)
    # artifact block landed
    assert any(
        a.get("id") == "art_1"
        for a in (env.get("extensions") or {}).get("gallomd_artifacts", [])
    )
    # evidence ref landed
    refs = env["evidence"]["refs"]
    assert any(r.get("evidence_id") == "ev_1" for r in refs)
    # semantic_intent landed
    units = env["gallounits"]["units"]
    matches = [u for u in units if u.get("unit_id") == "u-h-0001"]
    assert matches
    assert matches[0]["semantic_intent"] == "invoice_to_employee_approver"


def test_vocabulary_constant_matches_starter_set() -> None:
    """The vocabulary constant tracks docs/specs/gallodoc-semantic-intent-v3.md §2."""
    expected = {
        "invoice_to_employee_approver",
        "contract_supersedes_contract",
        "patient_to_consent_record",
        "claim_to_supporting_document",
        "case_to_case_continuation",
        "attachment_to_parent_document",
    }
    assert set(SEMANTIC_INTENT_VOCABULARY) == expected


def test_dispatch_table_recognizes_semantic_intent() -> None:
    """The dispatch table routes ``::semantic_intent`` to the handler."""
    from gallodoc.markdown import _BLOCK_DISPATCH  # type: ignore[attr-defined]
    assert _BLOCK_DISPATCH.get("semantic_intent") == "semantic_intent"


def test_no_ml_dependencies_in_linking_package() -> None:
    """Sanity: gallodoc.linking does not import any ML library."""
    import gallodoc.linking  # noqa: F401
    import gallodoc.linking.linker  # noqa: F401
    import gallodoc.linking.scoring  # noqa: F401
    import gallodoc.linking.rules  # noqa: F401
    import gallodoc.linking.evidence  # noqa: F401
    import sys

    for mod_name in ("torch", "tensorflow", "sentence_transformers", "transformers", "sklearn", "numpy"):
        assert mod_name not in sys.modules or sys.modules[mod_name] is None or True, (
            # We don't fail if something else imported numpy — only assert
            # nothing in gallodoc.linking imported these. Use module inspection.
            ""
        )
    # Stronger check: walk gallodoc/linking source files for import statements.
    import pathlib
    linking_dir = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "gallodoc" / "linking"
    forbidden_imports = ("torch", "tensorflow", "sentence_transformers", "transformers", "sklearn", "numpy")
    for py_file in linking_dir.glob("*.py"):
        text = py_file.read_text()
        for forbidden in forbidden_imports:
            assert f"import {forbidden}" not in text, f"{py_file.name} imports {forbidden}"
            assert f"from {forbidden}" not in text, f"{py_file.name} imports from {forbidden}"
