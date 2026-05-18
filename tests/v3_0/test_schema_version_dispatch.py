"""validate_envelope() must dispatch by schema_version (exact-match).

The dispatch contract:

- ``"gallodoc-core/v1"`` → ``_validate_v1`` — preserves the original v1 behavior.
- ``"gallodoc-core/v3"`` → ``_validate_v3`` — applies v3 structural + carry-forward rules.
- anything else (including missing) → ``valid=False`` with "unknown schema version".

These tests probe the dispatch — not the per-version validator internals.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
V1_EXAMPLE = PACKAGE_ROOT / "examples" / "gallodoc_pdf_contract.json"


def test_v1_envelope_routes_to_v1_validator():
    """A v1 envelope dispatches to _validate_v1 — which produces v1-specific
    structural results (the v1 bare-array `relationships` shape passes there
    but would fail under v3, because v3 requires an object)."""
    env = json.loads(V1_EXAMPLE.read_text(encoding="utf-8"))
    assert env["schema_version"] == "gallodoc-core/v1"
    # The v1 envelope's `relationships` is a bare list. Under v3 dispatch
    # it would trigger "expected type object" — but under v1 dispatch it
    # passes.
    assert isinstance(env["relationships"], list)
    result = validate_envelope(env)
    assert result.valid, f"v1 example must validate under v1 dispatch: {[(i.path, i.message) for i in result.errors()][:5]}"
    # The dispatched path did NOT raise "expected type object" for relationships,
    # confirming v1-not-v3 was chosen.
    rel_object_errors = [
        i for i in result.issues if i.path == "relationships" and "expected type object" in i.message
    ]
    assert not rel_object_errors, "dispatch incorrectly routed v1 envelope through v3 path"


def test_v3_envelope_routes_to_v3_validator():
    """A v3 envelope dispatches to _validate_v3, which expects the v3
    object-shaped `relationships`. If dispatch were incorrect (v1), v3's
    object relationships would trip the v1 bare-array structural rule."""
    env = minimal_v3_envelope()
    assert env["schema_version"] == "gallodoc-core/v3"
    assert isinstance(env["relationships"], dict)
    result = validate_envelope(env)
    assert result.valid, f"minimal v3 envelope must validate under v3 dispatch: {[(i.path, i.message) for i in result.errors()][:5]}"


def test_unknown_v2_schema_version_returns_invalid():
    """An envelope declaring `gallodoc-core/v2` (no such schema exists)
    routes through the unknown-version branch."""
    env = minimal_v3_envelope()
    env["schema_version"] = "gallodoc-core/v2"
    result = validate_envelope(env)
    assert not result.valid
    issues = [(i.path, i.message) for i in result.errors()]
    assert any(
        i_path == "schema_version" and "unknown schema version" in i_msg
        for i_path, i_msg in issues
    ), f"expected unknown-version dispatch, got {issues}"


def test_missing_schema_version_returns_invalid():
    """An envelope with no schema_version key routes through the
    unknown-version branch (does not crash)."""
    env = minimal_v3_envelope()
    env.pop("schema_version", None)
    result = validate_envelope(env)
    assert not result.valid
    issues = [(i.path, i.message) for i in result.errors()]
    assert any(
        i_path == "schema_version" and "unknown schema version" in i_msg
        for i_path, i_msg in issues
    ), f"expected unknown-version dispatch, got {issues}"


def test_empty_dict_routes_through_unknown_version_branch():
    """Bare `{}` triggers the unknown-version branch, not a crash."""
    result = validate_envelope({})
    assert not result.valid
    issues = [(i.path, i.message) for i in result.errors()]
    # Either "unknown schema version" or a generic structural complaint
    # mentioning schema_version is acceptable; both end up at path=schema_version.
    assert any(i_path == "schema_version" for i_path, _ in issues)


def test_nonstring_schema_version_does_not_crash():
    """A non-string schema_version value (e.g. a number) does not raise;
    the dispatch returns invalid with a recognizable message."""
    env = minimal_v3_envelope()
    env["schema_version"] = 3
    result = validate_envelope(env)
    assert not result.valid


def test_envelope_must_be_dict():
    """Passing anything other than a dict returns invalid without crashing."""
    result = validate_envelope([])  # type: ignore[arg-type]
    assert not result.valid
    assert any("must be a JSON object" in i.message for i in result.errors())
