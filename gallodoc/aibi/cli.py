"""``gallodoc aibi plan`` CLI subcommand.

Wires the NL→GQL planner into the main ``gallodoc`` argparser.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from gallodoc.aibi.planner import plan as run_plan
from gallodoc.aibi.safe_filters import UnsafePlanError


def cli_aibi_plan(
    nl: str,
    envelope_path: str | None,
    check_only: bool,
    out_path: str | None,
) -> int:
    """Run the planner from CLI arguments. Returns an exit code."""
    envelope: dict[str, Any] | None = None
    if envelope_path:
        try:
            envelope = json.loads(Path(envelope_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"failed to read envelope {envelope_path!r}: {exc}\n")
            return 2

    try:
        plan_obj = run_plan(nl, envelope)
    except UnsafePlanError as exc:
        sys.stderr.write(f"unsafe plan: {exc}\n")
        return 3
    except ValueError as exc:
        sys.stderr.write(f"planner error: {exc}\n")
        return 2

    payload = plan_obj.to_dict()

    if check_only:
        sys.stdout.write("OK — plan would be safe\n")
        return 0

    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if out_path:
        try:
            Path(out_path).write_text(rendered, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"failed to write {out_path!r}: {exc}\n")
            return 2
    else:
        sys.stdout.write(rendered)
    return 0


def _cmd_aibi_plan(args: argparse.Namespace) -> int:
    return cli_aibi_plan(
        nl=args.nl,
        envelope_path=args.envelope,
        check_only=args.check_only,
        out_path=args.out,
    )


def add_aibi_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``aibi`` subcommand on the main argparser."""
    p_aibi = subparsers.add_parser(
        "aibi",
        help="AI/BI commands — NL → query plan (Codex 09).",
    )
    aibi_sub = p_aibi.add_subparsers(dest="aibi_command", required=True)

    p_plan = aibi_sub.add_parser(
        "plan",
        help=(
            "Plan a natural-language query against the v2.0 query_access (GQL) grammar. "
            "Emits structured JSON; never raw SQL."
        ),
    )
    p_plan.add_argument(
        "nl",
        help="natural-language query string",
    )
    p_plan.add_argument(
        "--envelope",
        default=None,
        help="optional path to a JSON envelope used as planning context",
    )
    p_plan.add_argument(
        "--check-only",
        action="store_true",
        help="validate that the plan would be safe; do not write any output file",
    )
    p_plan.add_argument(
        "--out",
        default=None,
        help="optional path to write the plan JSON (otherwise stdout)",
    )
    p_plan.set_defaults(func=_cmd_aibi_plan)


__all__ = [
    "cli_aibi_plan",
    "add_aibi_parser",
]
