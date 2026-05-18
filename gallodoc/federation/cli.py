"""CLI dispatch for ``gallodoc federation match ...``.

The ``gallodoc`` binary in ``gallodoc/cli/main.py`` wires ``federation``
as a top-level subcommand. This module owns the dispatch logic so the
binary stays small and the federation machinery stays inside
``gallodoc.federation``.
"""

from __future__ import annotations

import argparse
import glob as _glob
import json
import sys
from pathlib import Path
from typing import Any

from gallodoc.federation import (
    apply_federation_policy,
    build_matching_receipts,
    cross_tenant_link,
)
from gallodoc.linking import LinkerOutput


def _load_envelope(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            f"expected an envelope object in {path}, got {type(payload).__name__}"
        )
    return payload


def _load_targets(spec: str) -> list[dict[str, Any]]:
    """Load target envelopes from a path or a glob.

    Two accepted forms:
      - A path to a JSON file containing a JSON array of envelopes
        OR a single envelope object.
      - A glob expression matching multiple JSON files (each a single
        envelope object).
    """
    # Try glob expansion first. If glob returns multiple files, treat as
    # one envelope per file. Otherwise fall back to JSON-file parsing.
    matches = sorted(_glob.glob(spec))
    if len(matches) > 1:
        return [_load_envelope(Path(m)) for m in matches]
    # Single path (either from glob or literal)
    p = Path(matches[0]) if matches else Path(spec)
    if not p.exists():
        raise FileNotFoundError(f"targets file not found: {spec}")
    payload = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        envelopes: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError(
                    "targets array must contain envelope objects"
                )
            envelopes.append(item)
        return envelopes
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(
        f"targets must be a glob, a JSON array of envelopes, or an envelope object — got {type(payload).__name__}"
    )


def cli_federation_match(
    source_path: str,
    targets_spec: str,
    out_path: str,
    *,
    min_confidence: float = 0.10,
) -> dict[str, Any]:
    """Run federation-enforced linking and write an output envelope.

    The output is a copy of the source envelope with:
      - The linker's surviving candidates written into
        ``relationships.relationships[]`` (status: ``"suggested"``,
        ``discovered_by: "gallodoc-linker/3.0.0"``).
      - ``federation.matching_receipts[]`` populated, one entry per
        surviving candidate (``raw_data_exposed: false``).

    Returns the output envelope (also written to ``out_path``).
    """
    src = _load_envelope(Path(source_path))
    targets = _load_targets(targets_spec)

    # Run the federation-enforced linker; this already does per-target
    # intersection and filtering.
    linker_out = cross_tenant_link(src, targets, min_confidence=min_confidence)

    # Build matching receipts per-target so each receipt's source/target
    # profile_ref is correct.
    all_receipts: list[dict[str, Any]] = []
    for tgt in targets:
        tgt_id = (tgt.get("identity") or {}).get("gallodoc_id")
        per_target_out = LinkerOutput(
            source_document_id=linker_out.source_document_id,
            candidates=[
                c for c in linker_out.candidates if c.target_document_id == tgt_id
            ],
        )
        all_receipts.extend(build_matching_receipts(src, tgt, per_target_out))

    # Build output envelope: copy source, write candidates into relationships,
    # write receipts into federation.matching_receipts[].
    out_env: dict[str, Any] = json.loads(json.dumps(src))  # deep copy via JSON
    rel_block = out_env.get("relationships")
    if not isinstance(rel_block, dict):
        rel_block = {"relationships": []}
        out_env["relationships"] = rel_block
    rel_entries = rel_block.setdefault("relationships", [])
    existing_ids = {
        e.get("relationship_id")
        for e in rel_entries
        if isinstance(e, dict) and e.get("relationship_id")
    }
    for c in linker_out.candidates:
        if c.relationship_id in existing_ids:
            continue
        rel_entries.append(c.to_dict())
        existing_ids.add(c.relationship_id)

    fed_block = out_env.get("federation")
    if not isinstance(fed_block, dict):
        fed_block = {"schema_version": "gallodoc.federation.v3.0"}
        out_env["federation"] = fed_block
    fed_block["matching_receipts"] = list(all_receipts)

    Path(out_path).write_text(
        json.dumps(out_env, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_env


def cmd_federation_match(args: argparse.Namespace) -> int:
    try:
        env = cli_federation_match(
            source_path=args.source,
            targets_spec=args.targets,
            out_path=args.out,
            min_confidence=float(args.min_confidence),
        )
    except FileNotFoundError as exc:
        sys.stderr.write(f"gallodoc federation match: {exc}\n")
        return 1
    except (ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"gallodoc federation match: {exc}\n")
        return 1

    receipts = (env.get("federation") or {}).get("matching_receipts") or []
    rels = ((env.get("relationships") or {}).get("relationships") or [])
    summary = {
        "source": args.source,
        "targets": args.targets,
        "out": args.out,
        "candidates_written": len(rels),
        "matching_receipts": len(receipts),
    }
    if args.json:
        sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    else:
        for k, v in summary.items():
            sys.stdout.write(f"{k}: {v}\n")
    return 0


def add_federation_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``federation`` subcommand on the main argparser."""
    p_fed = subparsers.add_parser(
        "federation",
        help="Federation commands (cross-tenant matching).",
    )
    fed_sub = p_fed.add_subparsers(dest="federation_command", required=True)

    p_match = fed_sub.add_parser(
        "match",
        help=(
            "Run federation-enforced linking — produces an output envelope "
            "with relationships.relationships[] + federation.matching_receipts[]."
        ),
    )
    p_match.add_argument(
        "--source",
        required=True,
        help="path to the source v3 envelope JSON",
    )
    p_match.add_argument(
        "--targets",
        required=True,
        help=(
            "path to a JSON file containing an array of target envelopes, "
            "or a glob expression matching multiple JSON files (each a single envelope)"
        ),
    )
    p_match.add_argument(
        "--out",
        required=True,
        help="path to write the output envelope JSON",
    )
    p_match.add_argument(
        "--min-confidence",
        default=0.10,
        type=float,
        help="minimum linker confidence before federation enforcement (default: 0.10)",
    )
    p_match.add_argument(
        "--json",
        action="store_true",
        help="emit JSON status to stdout",
    )
    p_match.set_defaults(func=cmd_federation_match)


__all__ = [
    "add_federation_parser",
    "cli_federation_match",
    "cmd_federation_match",
]
