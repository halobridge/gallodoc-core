"""CLI dispatch for ``gallodoc connector ...`` subcommands.

The ``gallodoc`` binary in ``gallodoc/cli/main.py`` wires ``connector``
as a top-level subcommand with ``convert`` as its only action today.
This module owns the dispatch logic so the binary stays small and the
connector machinery stays in the ``gallodoc.connectors`` package.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def cli_connector_convert(
    connector_slug: str, input_path: str, out_path: str
) -> int:
    """Run a starter connector and write its output(s) to ``out_path``.

    Returns ``0`` on success, ``1`` on a bad slug, missing input, or
    write error. Stderr carries the human-readable error message.
    """
    # Late import to keep stdlib-only path fast for unrelated CLI calls.
    from gallodoc.connectors import CONNECTORS  # noqa: PLC0415

    connector_cls = CONNECTORS.get(connector_slug)
    if connector_cls is None:
        sys.stderr.write(
            f"gallodoc connector convert: unknown connector slug "
            f"{connector_slug!r}. Available: {sorted(CONNECTORS)}\n"
        )
        return 1

    src = Path(input_path)
    if not src.exists():
        sys.stderr.write(
            f"gallodoc connector convert: input not found: {input_path}\n"
        )
        return 1

    connector = connector_cls()
    source: Any = src
    # JSON-shape connectors take a parsed dict/list. The CSV and PDF
    # connectors take a path directly.
    if connector_slug in ("generic_json", "salesforce_account_stub", "invoice_stub"):
        try:
            source = json.loads(src.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(
                f"gallodoc connector convert: failed to parse input as JSON: {exc}\n"
            )
            return 1

    try:
        envelopes = list(connector.to_envelopes(source))
    except Exception as exc:  # pragma: no cover — defensive
        sys.stderr.write(f"gallodoc connector convert: connector failed: {exc}\n")
        return 1

    if not envelopes:
        sys.stderr.write(
            "gallodoc connector convert: connector produced zero envelopes\n"
        )
        return 1

    out: Any = envelopes[0] if len(envelopes) == 1 else envelopes
    try:
        Path(out_path).write_text(
            json.dumps(out, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        sys.stderr.write(
            f"gallodoc connector convert: failed to write {out_path}: {exc}\n"
        )
        return 1

    sys.stdout.write(
        f"wrote {out_path} ({len(envelopes)} envelope"
        + ("s" if len(envelopes) != 1 else "")
        + ")\n"
    )
    return 0


def cmd_connector_convert(args: argparse.Namespace) -> int:
    """argparse-facing wrapper around ``cli_connector_convert``."""
    return cli_connector_convert(args.connector, args.input, args.out)


def add_connector_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``connector`` subcommand on the main argparser."""
    p_connector = subparsers.add_parser(
        "connector",
        help="Open Connector SDK commands (convert input to a v3 envelope).",
    )
    connector_sub = p_connector.add_subparsers(
        dest="connector_command", required=True
    )

    p_convert = connector_sub.add_parser(
        "convert",
        help="Convert an input file to a v3 GalloDoc envelope using a named connector.",
    )
    p_convert.add_argument(
        "--connector",
        required=True,
        help="connector slug (e.g. generic_json, csv_row, pdf_file_metadata, "
        "salesforce_account_stub, invoice_stub)",
    )
    p_convert.add_argument(
        "--input",
        required=True,
        help="path to the input file",
    )
    p_convert.add_argument(
        "--out",
        required=True,
        help="path to write the resulting envelope JSON",
    )
    p_convert.set_defaults(func=cmd_connector_convert)


__all__ = [
    "cli_connector_convert",
    "cmd_connector_convert",
    "add_connector_parser",
]
