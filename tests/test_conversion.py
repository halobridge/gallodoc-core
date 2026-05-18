"""Tests for the document conversion layer (Core 2.1).

Covers stdlib-supported formats (txt, md, json, csv, html, xml, eml) plus
graceful fallback paths for optional formats (pdf, docx, xlsx).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.conversion import (
    ConversionError,
    build_gallomd_from_text,
    convert_file_to_gallodoc,
    convert_file_to_gallomd,
    detect_input_type,
)
from gallodoc.markdown import gallomd_to_gallodoc
from gallodoc.validation import validate_envelope


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples" / "conversion"


def _write_tmp(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_detect_input_type_known_extensions() -> None:
    assert detect_input_type("a.txt") == "txt"
    assert detect_input_type("a.md") == "markdown"
    assert detect_input_type("a.gmd") == "gallomarkdown"
    assert detect_input_type("a.json") == "json"
    assert detect_input_type("a.csv") == "csv"
    assert detect_input_type("a.pdf") == "pdf"
    assert detect_input_type("a.docx") == "docx"
    assert detect_input_type("a.xlsx") == "xlsx"
    assert detect_input_type("a.eml") == "eml"
    # unknown extension falls back to txt
    assert detect_input_type("a.unknown") == "txt"


def test_txt_converts_to_gallomd_and_gallodoc(tmp_path: Path) -> None:
    src = _write_tmp(tmp_path, "note.txt", "Quarterly Review\n\nAll initiatives closed on 2026-04-30.\n")
    result = convert_file_to_gallomd(src, extract_artifacts=True)
    assert result.input_type == "txt"
    assert "::gallodoc" in result.gallomd
    assert "::artifact" in result.gallomd  # one date should be extracted
    env = result.gallodoc
    assert env["schema_version"] == "gallodoc-core/v1"
    assert env["identity"]["document_type"] == "text_document"
    val = validate_envelope(env)
    assert val.valid, [(i.path, i.message) for i in val.issues if i.severity == "error"]


def test_markdown_input_passes_through_as_content(tmp_path: Path) -> None:
    src = _write_tmp(tmp_path, "doc.md", "# A heading\n\nA paragraph here.\n")
    result = convert_file_to_gallomd(src)
    assert result.input_type == "markdown"
    assert "# A heading" in result.gallomd or "A heading" in result.gallomd


def test_json_input_is_summarized(tmp_path: Path) -> None:
    payload = {"id": "x", "value": 42, "items": [1, 2, 3]}
    src = _write_tmp(tmp_path, "data.json", json.dumps(payload))
    result = convert_file_to_gallomd(src)
    assert result.input_type == "json"
    assert "## Structured Source" in result.gallomd
    val = validate_envelope(result.gallodoc)
    assert val.valid


def test_csv_input_renders_table(tmp_path: Path) -> None:
    src = _write_tmp(tmp_path, "rows.csv", "a,b\n1,2\n3,4\n")
    result = convert_file_to_gallomd(src)
    assert result.input_type == "csv"
    assert "| a | b |" in result.gallomd


def test_gallomd_input_compiles_directly(tmp_path: Path) -> None:
    src = _write_tmp(
        tmp_path,
        "demo.gmd",
        "# Demo\n\n::gallodoc\ndoc_id: doc-direct-001\ndocument_type: demo\n::\n\n## Content\n\nbody\n",
    )
    result = convert_file_to_gallomd(src)
    assert result.input_type == "gallomarkdown"
    assert result.gallodoc["identity"]["gallodoc_id"] == "doc-direct-001"


def test_generated_gallomd_compiles_back_to_valid_envelope(tmp_path: Path) -> None:
    src = _write_tmp(tmp_path, "msg.txt", "Hello world. Contact ops@example.com.\n")
    result = convert_file_to_gallomd(src, extract_artifacts=True)
    env_again = gallomd_to_gallodoc(result.gallomd)
    assert env_again["schema_version"] == "gallodoc-core/v1"
    val = validate_envelope(env_again)
    assert val.valid


def test_forbidden_raw_prompt_in_text_is_redacted_by_default(tmp_path: Path) -> None:
    src = _write_tmp(
        tmp_path,
        "leak.txt",
        "Bearer abcdefghijklmnopqrstuvwxyz1234567 was stored.\n",
    )
    result = convert_file_to_gallomd(src)
    assert "[REDACTED]" in result.gallomd
    assert any("redacted" in w.lower() for w in result.warnings)


def test_raw_mode_rejects_unsafe_text(tmp_path: Path) -> None:
    src = _write_tmp(
        tmp_path,
        "leak.txt",
        "PEM block: -----BEGIN RSA PRIVATE KEY-----abc-----END RSA PRIVATE KEY-----\n",
    )
    with pytest.raises(ConversionError):
        convert_file_to_gallomd(src, redaction_mode="raw")


def test_pdf_conversion_falls_back_when_pypdf_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip_or_skip = None  # placate type checkers
    src = _write_tmp(tmp_path, "fake.pdf", "")
    # Even without pypdf installed the CLI must not crash — it returns
    # an envelope with a placeholder body and a warning.
    try:
        import pypdf  # type: ignore  # noqa: F401, PLC0415
        pytest.skip("pypdf is installed; fallback path not exercised in this environment.")
    except ImportError:
        pass
    result = convert_file_to_gallomd(src)
    assert result.input_type == "pdf"
    assert any("pypdf" in w.lower() for w in result.warnings)


def test_docx_conversion_falls_back_when_python_docx_missing(tmp_path: Path) -> None:
    src = _write_tmp(tmp_path, "fake.docx", "")
    try:
        import docx  # type: ignore  # noqa: F401, PLC0415
        pytest.skip("python-docx is installed; fallback path not exercised here.")
    except ImportError:
        pass
    result = convert_file_to_gallomd(src)
    assert result.input_type == "docx"
    assert any("python-docx" in w.lower() for w in result.warnings)


def test_build_gallomd_from_text_returns_gmd_string() -> None:
    text = "Hello world.\n"
    gmd, artifacts, warnings = build_gallomd_from_text(text, title="Hello", document_type="note")
    assert gmd.startswith("# Hello")
    assert "::gallodoc" in gmd
    assert artifacts == []
    assert warnings == []


def test_text_artifact_extraction_finds_dates_and_amounts() -> None:
    text = "Closed on 2026-04-15 with cost $1,234.56.\n"
    _, artifacts, _ = build_gallomd_from_text(
        text, title="X", document_type="note", extract_artifacts=True
    )
    families = {a["family"] for a in artifacts}
    assert "dates" in families
    assert "amounts" in families


def test_convert_file_to_gallodoc_returns_envelope(tmp_path: Path) -> None:
    src = _write_tmp(tmp_path, "n.txt", "Just a note.\n")
    env = convert_file_to_gallodoc(src)
    assert env["schema_version"] == "gallodoc-core/v1"


def test_pre_generated_conversion_examples_validate() -> None:
    """The sample.gallodoc.json files committed under examples/conversion must validate."""
    if not EXAMPLES.exists():
        pytest.skip("conversion examples not present in this checkout")
    found = False
    for child in EXAMPLES.iterdir():
        if not child.is_dir():
            continue
        envelope_path = child / "sample.gallodoc.json"
        if not envelope_path.exists():
            continue
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        result = validate_envelope(envelope)
        assert result.valid, f"{envelope_path}: {[(i.path, i.message) for i in result.issues if i.severity == 'error']}"
        found = True
    assert found, "expected at least one example conversion artefact"
