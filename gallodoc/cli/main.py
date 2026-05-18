"""``gallodoc`` command-line entry point.

Subcommands:

* ``validate <file> [<file> ...]`` — validate one or more GalloDoc envelopes (v1.0 core and v1.1–v1.3 amendment examples).
* ``inspect <file>``   — print a human-friendly summary.
* ``units <file>``     — segment a text file into GalloUnits.
* ``extract <file>``   — extract basic artifacts from a text file.
* ``gstp verify <path>`` — verify a GSTP package or manifest.

All subcommands accept ``--json`` for machine-readable output and exit ``0``
on success / ``1`` on failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from gallodoc import GALLODOC_CORE_VERSION, __version__
from gallodoc.ai_usage import summarize_ai_usage
from gallodoc.artifacts import extract_basic_artifacts
from gallodoc.aibi.cli import add_aibi_parser
from gallodoc.connectors.cli import add_connector_parser
from gallodoc.federation.cli import add_federation_parser
from gallodoc.semantic.embeddings.cli import add_semantic_parser
from gallodoc.training.cli import add_training_parser
from gallodoc.conversion import (
    ConversionError,
    ConversionResult,
    convert_file_to_gallomd,
)
from gallodoc.gstp import verify_gstp_package
from gallodoc.markdown import (
    GalloMDError,
    gallomd_to_gallodoc,
    parse_gallomd,
    validate_gallomd,
)
from gallodoc.markdown_renderer import gallodoc_to_gallomd
from gallodoc.units import build_gallounits_block
from gallodoc.validation import (
    ValidationResult,
    load_envelope,
    validate_envelope,
    validate_with_jsonschema,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _print(payload: Any, json_out: bool) -> None:
    if json_out:
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    else:
        if isinstance(payload, dict):
            for k, v in payload.items():
                sys.stdout.write(f"{k}: {v}\n")
        elif isinstance(payload, list):
            for item in payload:
                sys.stdout.write(f"- {item}\n")
        else:
            sys.stdout.write(f"{payload}\n")


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def cmd_validate(args: argparse.Namespace) -> int:
    paths: list[str] = list(args.files)
    rc = 0
    single_json: dict[str, Any] | None = None
    multi_json: list[dict[str, Any]] | None = None
    if args.json and len(paths) > 1:
        multi_json = []

    for fp in paths:
        try:
            envelope = load_envelope(fp)
        except FileNotFoundError:
            sys.stderr.write(f"gallodoc validate: file not found: {fp}\n")
            rc = 1
            continue
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"gallodoc validate: invalid JSON in {fp} ({exc.msg} at line {exc.lineno})\n")
            rc = 1
            continue

        if args.use_jsonschema:
            result = validate_with_jsonschema(envelope)
        else:
            result = validate_envelope(envelope)

        if args.json:
            if len(paths) == 1:
                single_json = result.to_dict()
            elif multi_json is not None:
                multi_json.append({"file": fp, **result.to_dict()})
        else:
            _render_validation_human(fp, result)

        if not result.valid:
            rc = 1

    if args.json:
        if len(paths) == 1 and single_json is not None:
            _print(single_json, json_out=True)
        elif multi_json is not None:
            _print(multi_json, json_out=True)

    return rc


def _render_validation_human(filename: str, result: ValidationResult) -> None:
    sys.stdout.write(f"file: {filename}\n")
    sys.stdout.write(f"schema_version: {result.schema_version or '(missing)'}\n")
    sys.stdout.write(f"used_jsonschema: {result.used_jsonschema}\n")
    sys.stdout.write(f"valid: {result.valid}\n")
    errors = [i for i in result.issues if i.severity == "error"]
    warnings = [i for i in result.issues if i.severity == "warning"]
    if errors:
        sys.stdout.write("errors:\n")
        for issue in errors:
            sys.stdout.write(f"  - {issue.path}: {issue.message}\n")
    if warnings:
        sys.stdout.write("warnings:\n")
        for issue in warnings:
            sys.stdout.write(f"  - {issue.path}: {issue.message}\n")


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


def cmd_inspect(args: argparse.Namespace) -> int:
    try:
        env = load_envelope(args.file)
    except FileNotFoundError:
        sys.stderr.write(f"gallodoc inspect: file not found: {args.file}\n")
        return 1
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"gallodoc inspect: invalid JSON ({exc.msg})\n")
        return 1

    identity = env.get("identity") or {}
    source = env.get("source") or {}
    gallounits = env.get("gallounits") or {}
    ai_usage = env.get("ai_usage") or {}
    certification = env.get("certification") or {}
    gstp = env.get("gstp") or {}
    truth_ledger = env.get("truth_ledger") or {}
    exec_gov = env.get("execution_governance") if isinstance(env.get("execution_governance"), dict) else {}

    summary = {
        "file": args.file,
        "schema_version": env.get("schema_version", ""),
        "document_id": identity.get("document_id") or identity.get("gallodoc_id") or "",
        "document_type": identity.get("document_type", ""),
        "title": identity.get("title", ""),
        "source": {
            "system": source.get("source_system", ""),
            "kind": source.get("source_kind", ""),
            "connector_slug": source.get("connector_slug", ""),
        },
        "gallounit_count": len(gallounits.get("units") or []),
        "model_projection_count": len(gallounits.get("model_projections") or []),
        "ai_usage_totals": ai_usage.get("summary") or summarize_ai_usage(ai_usage.get("runs") or []),
        "certification_status": certification.get("status", ""),
        "certification_type": certification.get("certification_type", ""),
        "gstp_status": gstp.get("status", ""),
        "gstp_package_id": gstp.get("package_id", ""),
        "truth_ledger_state": truth_ledger.get("truth_state", ""),
        "execution_governance_schema": exec_gov.get("schema_version", ""),
        "execution_receipt_count": len(exec_gov.get("execution_receipts") or []),
        "execution_request_count": len(exec_gov.get("execution_requests") or []),
    }
    _print(summary, json_out=args.json)
    return 0


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------


def cmd_units(args: argparse.Namespace) -> int:
    try:
        text = _read_text(args.file)
    except FileNotFoundError:
        sys.stderr.write(f"gallodoc units: file not found: {args.file}\n")
        return 1
    block = build_gallounits_block(text, classify=not args.no_classify)
    if args.json:
        _print(block, json_out=True)
        return 0
    sys.stdout.write(f"unit_strategy: {block['unit_strategy']}\n")
    sys.stdout.write(f"canonical_text_hash: {block['canonical_text_hash']}\n")
    sys.stdout.write(f"unit_count: {len(block['units'])}\n")
    for unit in block["units"]:
        sys.stdout.write(
            f"- {unit['unit_id']} [{unit['unit_type']}/{unit['semantic_role']}] "
            f"({unit['confidence']}) {unit['content_summary'][:120]}\n"
        )
    return 0


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------


def cmd_extract(args: argparse.Namespace) -> int:
    try:
        text = _read_text(args.file)
    except FileNotFoundError:
        sys.stderr.write(f"gallodoc extract: file not found: {args.file}\n")
        return 1
    units = build_gallounits_block(text, classify=True)["units"]
    artifacts = extract_basic_artifacts(units)
    if args.json:
        _print({"artifact_count": len(artifacts), "artifacts": artifacts}, json_out=True)
        return 0
    sys.stdout.write(f"artifact_count: {len(artifacts)}\n")
    for art in artifacts:
        sys.stdout.write(
            f"- {art['artifact_type']} ({art['confidence']}, needs_review={art['needs_review']}): "
            f"{art['value_summary']}\n"
        )
    return 0


# ---------------------------------------------------------------------------
# gstp verify
# ---------------------------------------------------------------------------


def cmd_gstp_verify(args: argparse.Namespace) -> int:
    pub_key = None
    if args.public_key:
        try:
            pub_key = Path(args.public_key).read_text(encoding="utf-8")
        except FileNotFoundError:
            sys.stderr.write(f"gallodoc gstp verify: public key not found: {args.public_key}\n")
            return 1
    result = verify_gstp_package(args.path, public_key=pub_key)
    if args.json:
        _print(result.to_dict(), json_out=True)
    else:
        sys.stdout.write(f"path: {args.path}\n")
        sys.stdout.write(f"package_id: {result.package_id}\n")
        sys.stdout.write(f"package_type: {result.package_type}\n")
        sys.stdout.write(f"manifest_hash_ok: {result.manifest_hash_ok}\n")
        sys.stdout.write(f"payload_hash_ok: {result.payload_hash_ok}\n")
        sys.stdout.write(f"signature_ok: {result.signature_ok}\n")
        sys.stdout.write(f"valid: {result.valid}\n")
        if result.issues:
            sys.stdout.write("issues:\n")
            for i in result.issues:
                sys.stdout.write(f"  - {i}\n")
        if result.warnings:
            sys.stdout.write("warnings:\n")
            for w in result.warnings:
                sys.stdout.write(f"  - {w}\n")
    return 0 if result.valid else 1


# ---------------------------------------------------------------------------
# md (GalloMarkdown) commands
# ---------------------------------------------------------------------------


def _read_gmd(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def cmd_md_validate(args: argparse.Namespace) -> int:
    try:
        text = _read_gmd(args.file)
    except FileNotFoundError:
        sys.stderr.write(f"gallodoc md validate: file not found: {args.file}\n")
        return 1
    try:
        validate_gallomd(text)
    except GalloMDError as exc:
        if args.json:
            _print({"file": args.file, "valid": False, "error": str(exc)}, json_out=True)
        else:
            sys.stderr.write(f"gallodoc md validate: {exc}\n")
        return 1
    if args.json:
        _print({"file": args.file, "valid": True}, json_out=True)
    else:
        sys.stdout.write(f"file: {args.file}\nvalid: True\n")
    return 0


def cmd_md_compile(args: argparse.Namespace) -> int:
    try:
        text = _read_gmd(args.file)
    except FileNotFoundError:
        sys.stderr.write(f"gallodoc md compile: file not found: {args.file}\n")
        return 1
    try:
        envelope = gallomd_to_gallodoc(text)
    except GalloMDError as exc:
        sys.stderr.write(f"gallodoc md compile: {exc}\n")
        return 1
    indent = 2 if args.pretty else None
    payload = json.dumps(envelope, indent=indent, sort_keys=args.pretty)
    if args.out:
        Path(args.out).write_text(payload + ("\n" if not payload.endswith("\n") else ""), encoding="utf-8")
        if not args.json:
            sys.stdout.write(f"wrote: {args.out}\n")
        else:
            _print({"file": args.file, "out": args.out, "valid": True}, json_out=True)
    else:
        sys.stdout.write(payload + "\n")
    return 0


def cmd_md_inspect(args: argparse.Namespace) -> int:
    try:
        text = _read_gmd(args.file)
    except FileNotFoundError:
        sys.stderr.write(f"gallodoc md inspect: file not found: {args.file}\n")
        return 1
    try:
        doc = parse_gallomd(text)
    except GalloMDError as exc:
        sys.stderr.write(f"gallodoc md inspect: {exc}\n")
        return 1
    summary = {
        "file": args.file,
        "title": doc.title,
        "block_count": len(doc.blocks),
        "blocks": [{"name": b.name, "line": b.line, "attrs": b.attrs} for b in doc.blocks],
        "heading_count": len(doc.headings),
        "paragraph_count": len(doc.paragraphs),
    }
    _print(summary, json_out=args.json)
    return 0


def cmd_md_render(args: argparse.Namespace) -> int:
    try:
        envelope = load_envelope(args.file)
    except FileNotFoundError:
        sys.stderr.write(f"gallodoc md render: file not found: {args.file}\n")
        return 1
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"gallodoc md render: invalid JSON ({exc.msg})\n")
        return 1
    rendered = gallodoc_to_gallomd(envelope)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
        if not args.json:
            sys.stdout.write(f"wrote: {args.out}\n")
        else:
            _print({"file": args.file, "out": args.out}, json_out=True)
    else:
        sys.stdout.write(rendered)
    return 0


def cmd_md_roundtrip(args: argparse.Namespace) -> int:
    try:
        text = _read_gmd(args.file)
    except FileNotFoundError:
        sys.stderr.write(f"gallodoc md roundtrip: file not found: {args.file}\n")
        return 1
    try:
        envelope = gallomd_to_gallodoc(text)
    except GalloMDError as exc:
        sys.stderr.write(f"gallodoc md roundtrip: compile failed — {exc}\n")
        return 1
    result = validate_envelope(envelope)
    rendered = gallodoc_to_gallomd(envelope)
    try:
        round_envelope = gallomd_to_gallodoc(rendered)
    except GalloMDError as exc:
        sys.stderr.write(f"gallodoc md roundtrip: rendered output did not re-compile — {exc}\n")
        return 1
    diffs = _diff_canonical_fields(envelope, round_envelope)
    payload = {
        "file": args.file,
        "valid": result.valid,
        "schema_version": envelope.get("schema_version"),
        "doc_id": (envelope.get("identity") or {}).get("gallodoc_id"),
        "render_length": len(rendered),
        "differences": diffs,
        "errors": [i.message for i in result.issues if i.severity == "error"],
    }
    _print(payload, json_out=args.json)
    return 0 if result.valid else 1


def _diff_canonical_fields(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """Compare canonical fields that should survive a roundtrip."""
    diffs: list[str] = []
    paths = (
        ("identity", "gallodoc_id"),
        ("identity", "document_id"),
        ("identity", "document_type"),
        ("identity", "title"),
        ("source", "source_system"),
        ("purpose", "primary_intent"),
    )
    for path in paths:
        v1 = a
        v2 = b
        for key in path:
            v1 = (v1 or {}).get(key) if isinstance(v1, dict) else None
            v2 = (v2 or {}).get(key) if isinstance(v2, dict) else None
        if v1 != v2:
            diffs.append(f"{'.'.join(path)}: {v1!r} != {v2!r}")
    # Counts of evidence/trust/decision/agent_security findings should match.
    def count(env: dict[str, Any], *path: str) -> int:
        cur: Any = env
        for key in path:
            cur = (cur or {}).get(key) if isinstance(cur, dict) else None
        return len(cur) if isinstance(cur, list) else 0
    for label, path in (
        ("evidence_refs", ("evidence", "refs")),
        ("trust_scores", ("trust_decision", "trust_scores")),
        ("decision_gates", ("trust_decision", "decision_gates")),
        ("policy_outcomes", ("trust_decision", "policy_outcomes")),
        ("agent_findings", ("agent_supply_chain_security", "findings")),
    ):
        c1 = count(a, *path)
        c2 = count(b, *path)
        if c1 != c2:
            diffs.append(f"{label}: {c1} != {c2}")
    return diffs


# ---------------------------------------------------------------------------
# convert (Core 2.1)
# ---------------------------------------------------------------------------


def cmd_convert(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        sys.stderr.write(f"gallodoc convert: file not found: {src}\n")
        return 1
    try:
        result = convert_file_to_gallomd(
            src,
            extract_artifacts=args.extract_artifacts,
            redaction_mode=args.redaction_mode,
        )
    except ConversionError as exc:
        sys.stderr.write(f"gallodoc convert: {exc}\n")
        return 1
    except GalloMDError as exc:
        sys.stderr.write(f"gallodoc convert: GalloMD compile failed — {exc}\n")
        return 1

    out_dir = Path(args.out_dir or src.parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem

    targets = args.to or "both"
    written: list[str] = []
    if targets in ("gmd", "both"):
        gmd_path = out_dir / f"{stem}.gmd"
        gmd_path.write_text(result.gallomd, encoding="utf-8")
        written.append(str(gmd_path))
    if targets in ("json", "both"):
        json_path = out_dir / f"{stem}.gallodoc.json"
        indent = 2 if args.pretty else None
        json_path.write_text(
            json.dumps(result.gallodoc, indent=indent, sort_keys=args.pretty) + "\n",
            encoding="utf-8",
        )
        written.append(str(json_path))

    validation: dict[str, Any] | None = None
    if args.validate:
        v = validate_envelope(result.gallodoc)
        validation = v.to_dict()

    payload = {
        "input_path": result.input_path,
        "input_type": result.input_type,
        "title": result.title,
        "outputs": written,
        "artifact_count": len(result.artifacts),
        "warnings": result.warnings,
        "validation": validation,
    }
    if args.json:
        _print(payload, json_out=True)
    else:
        sys.stdout.write(f"input_path: {payload['input_path']}\n")
        sys.stdout.write(f"input_type: {payload['input_type']}\n")
        sys.stdout.write(f"title: {payload['title']}\n")
        for path in written:
            sys.stdout.write(f"wrote: {path}\n")
        if result.artifacts:
            sys.stdout.write(f"artifacts: {len(result.artifacts)}\n")
        for w in result.warnings:
            sys.stdout.write(f"warning: {w}\n")
        if validation is not None:
            sys.stdout.write(f"validation.valid: {validation['valid']}\n")
            for err in validation.get("errors") or []:
                sys.stdout.write(f"validation.error: {err.get('path')}: {err.get('message')}\n")
    if validation is not None and not validation["valid"]:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Parser wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gallodoc",
        description="GalloDoc Core v1 — open-core CLI (package supports v1.0–v1.3 amendment examples)",
    )
    parser.add_argument("--version", action="version", version=f"gallodoc {__version__} ({GALLODOC_CORE_VERSION})")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Validate one or more GalloDoc envelopes (core + optional v1.1–v1.3 blocks).")
    p_validate.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="path to a GalloDoc JSON file (pass multiple files or use shell globs e.g. examples/v1_1/*.json)",
    )
    p_validate.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p_validate.add_argument("--use-jsonschema", action="store_true", help="use the jsonschema extra for full validation")
    p_validate.set_defaults(func=cmd_validate)

    p_inspect = sub.add_parser("inspect", help="Print a human-friendly summary.")
    p_inspect.add_argument("file", help="path to a GalloDoc JSON file")
    p_inspect.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p_inspect.set_defaults(func=cmd_inspect)

    p_units = sub.add_parser("units", help="Segment a text file into GalloUnits.")
    p_units.add_argument("file", help="path to a UTF-8 text file")
    p_units.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p_units.add_argument("--no-classify", action="store_true", help="skip rule-based classification")
    p_units.set_defaults(func=cmd_units)

    p_extract = sub.add_parser("extract", help="Extract basic artifacts from a text file.")
    p_extract.add_argument("file", help="path to a UTF-8 text file")
    p_extract.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p_extract.set_defaults(func=cmd_extract)

    p_gstp = sub.add_parser("gstp", help="GSTP commands.")
    gstp_sub = p_gstp.add_subparsers(dest="gstp_command", required=True)
    p_gstp_verify = gstp_sub.add_parser("verify", help="Verify a GSTP package or manifest.")
    p_gstp_verify.add_argument("path", help="path to a GSTP package directory or a manifest JSON")
    p_gstp_verify.add_argument("--public-key", default="", help="optional path to a PEM-encoded public key for signature verification")
    p_gstp_verify.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p_gstp_verify.set_defaults(func=cmd_gstp_verify)

    # md (GalloMarkdown) — bidirectional authoring/review layer.
    p_md = sub.add_parser(
        "md",
        help="GalloMarkdown commands (validate / compile / inspect / render / roundtrip).",
    )
    md_sub = p_md.add_subparsers(dest="md_command", required=True)

    p_md_validate = md_sub.add_parser("validate", help="Parse + safety-check a .gmd file.")
    p_md_validate.add_argument("file", help="path to a GalloMarkdown (.gmd) file")
    p_md_validate.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p_md_validate.set_defaults(func=cmd_md_validate)

    p_md_compile = md_sub.add_parser("compile", help="Compile a .gmd file into GalloDoc JSON.")
    p_md_compile.add_argument("file", help="path to a GalloMarkdown (.gmd) file")
    p_md_compile.add_argument("--out", default="", help="write JSON to this path instead of stdout")
    p_md_compile.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    p_md_compile.add_argument("--json", action="store_true", help="emit JSON status (when used with --out)")
    p_md_compile.set_defaults(func=cmd_md_compile)

    p_md_inspect = md_sub.add_parser("inspect", help="Print a structural summary of a .gmd file.")
    p_md_inspect.add_argument("file", help="path to a GalloMarkdown (.gmd) file")
    p_md_inspect.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p_md_inspect.set_defaults(func=cmd_md_inspect)

    p_md_render = md_sub.add_parser("render", help="Render a GalloDoc JSON envelope back to .gmd.")
    p_md_render.add_argument("file", help="path to a GalloDoc JSON envelope")
    p_md_render.add_argument("--out", default="", help="write the rendered .gmd to this path instead of stdout")
    p_md_render.add_argument("--json", action="store_true", help="emit JSON status (when used with --out)")
    p_md_render.set_defaults(func=cmd_md_render)

    p_md_roundtrip = md_sub.add_parser(
        "roundtrip",
        help="Compile .gmd → JSON → .gmd → JSON and report safe differences.",
    )
    p_md_roundtrip.add_argument("file", help="path to a GalloMarkdown (.gmd) file")
    p_md_roundtrip.add_argument("--json", action="store_true", help="emit JSON instead of text")
    p_md_roundtrip.set_defaults(func=cmd_md_roundtrip)

    # convert — Core 2.1 conversion layer (document → GalloMD + GalloDoc).
    p_convert = sub.add_parser(
        "convert",
        help="Convert a document (txt / md / json / csv / html / pdf / docx / xlsx / eml) to GalloMD + GalloDoc JSON.",
    )
    p_convert.add_argument("file", help="path to the document to convert")
    p_convert.add_argument("--to", choices=["gmd", "json", "both"], default="both", help="which artefacts to generate")
    p_convert.add_argument("--out-dir", default="", help="output directory (defaults to the source file's directory)")
    p_convert.add_argument("--redaction-mode", choices=["auto", "redacted", "raw"], default="auto", help="how to handle unsafe content")
    p_convert.add_argument("--validate", action="store_true", help="validate the compiled GalloDoc envelope after conversion")
    p_convert.add_argument("--pretty", action="store_true", help="pretty-print the generated JSON")
    p_convert.add_argument("--extract-artifacts", action="store_true", help="extract dates / amounts / emails / phones into ::artifact blocks")
    p_convert.add_argument("--json", action="store_true", help="emit JSON status to stdout")
    p_convert.set_defaults(func=cmd_convert)

    # connector — Open Connector SDK dispatch.
    add_connector_parser(sub)

    # semantic — embeddings + (future) other semantic commands.
    add_semantic_parser(sub)

    # training — embedder training lab (Codex 06).
    add_training_parser(sub)

    # federation — cross-tenant matching (Codex 08).
    add_federation_parser(sub)

    # aibi — NL → GQL planner (Codex 09).
    add_aibi_parser(sub)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
