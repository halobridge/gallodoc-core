"""CLI dispatch for ``gallodoc training export-pairs ...``.

The ``gallodoc`` binary in ``gallodoc/cli/main.py`` wires ``training``
as a top-level subcommand. This module owns the dispatch logic so the
binary stays small and the training machinery stays inside
``gallodoc.training``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _parse_ratios(s: str) -> tuple[float, float, float]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 3:
        raise ValueError(
            f"--ratios must be three comma-separated floats, got {s!r}"
        )
    try:
        a, b, c = (float(p) for p in parts)
    except ValueError as exc:
        raise ValueError(f"--ratios values must be floats: {s!r} ({exc})") from exc
    return (a, b, c)


def _load_input(path: Path) -> list[dict[str, Any]]:
    """Read input JSON. Returns a list of envelopes.

    Accepts either a single envelope (object with ``schema_version``) or
    a JSON array of envelopes.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        envelopes = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("input array must contain envelope objects")
            envelopes.append(item)
        return envelopes
    if isinstance(payload, dict):
        return [payload]
    raise ValueError(
        f"input must be an envelope object or a JSON array of envelopes, got {type(payload).__name__}"
    )


def _write_jsonl(path: Path, pairs: list) -> None:
    """Write a list of TrainingPair objects to JSONL at ``path``."""
    with path.open("w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p.to_dict(), sort_keys=True) + "\n")


def cli_training_export_pairs(
    input_path: str,
    out_path: str,
    seed: int,
    ratios_str: str | None,
    include_hard_negatives: bool,
) -> int:
    """Export training pairs from a v3 envelope (or a list of envelopes).

    Returns ``0`` on success, non-zero on error. Stderr carries the
    human-readable error message.
    """
    # Late imports keep stdlib-only path fast for unrelated CLI calls.
    from gallodoc.projection.safety import EnterpriseLeakageError  # noqa: PLC0415
    from gallodoc.training import (  # noqa: PLC0415
        assert_pairs_clean,
        extract_pairs_from_envelopes,
        generate_hard_negatives,
        split_train_dev_test,
    )

    src = Path(input_path)
    if not src.exists():
        sys.stderr.write(f"gallodoc training export-pairs: input not found: {input_path}\n")
        return 1

    try:
        envelopes = _load_input(src)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(
            f"gallodoc training export-pairs: failed to read input: {exc}\n"
        )
        return 1

    pairs = extract_pairs_from_envelopes(envelopes)

    if include_hard_negatives:
        pairs.extend(generate_hard_negatives(envelopes))

    try:
        assert_pairs_clean(pairs)
    except EnterpriseLeakageError as exc:
        sys.stderr.write(
            f"gallodoc training export-pairs: privacy scan failed: {exc}\n"
        )
        return 1

    out = Path(out_path)
    if ratios_str is None:
        try:
            _write_jsonl(out, pairs)
        except OSError as exc:
            sys.stderr.write(
                f"gallodoc training export-pairs: write failed: {exc}\n"
            )
            return 1
        return 0

    try:
        ratios = _parse_ratios(ratios_str)
    except ValueError as exc:
        sys.stderr.write(f"gallodoc training export-pairs: {exc}\n")
        return 1

    try:
        splits = split_train_dev_test(pairs, seed=seed, ratios=ratios)
    except ValueError as exc:
        sys.stderr.write(f"gallodoc training export-pairs: {exc}\n")
        return 1

    base = str(out)
    # Strip a trailing .jsonl so we don't get foo.jsonl.train.jsonl
    if base.endswith(".jsonl"):
        base = base[: -len(".jsonl")]

    try:
        _write_jsonl(Path(base + ".train.jsonl"), splits["train"])
        _write_jsonl(Path(base + ".dev.jsonl"), splits["dev"])
        _write_jsonl(Path(base + ".test.jsonl"), splits["test"])
    except OSError as exc:
        sys.stderr.write(
            f"gallodoc training export-pairs: write failed: {exc}\n"
        )
        return 1
    return 0


def cmd_training_export_pairs(args: argparse.Namespace) -> int:
    """argparse-facing wrapper around ``cli_training_export_pairs``."""
    return cli_training_export_pairs(
        input_path=args.input,
        out_path=args.out,
        seed=int(args.seed),
        ratios_str=args.ratios,
        include_hard_negatives=bool(args.include_hard_negatives),
    )


def add_training_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``training`` subcommand on the main argparser."""
    p_training = subparsers.add_parser(
        "training",
        help="Training-lab commands (export pairs from v3 envelopes).",
    )
    training_sub = p_training.add_subparsers(
        dest="training_command", required=True
    )

    p_export = training_sub.add_parser(
        "export-pairs",
        help="Export training pairs from a v3 envelope (or a list of envelopes).",
    )
    p_export.add_argument(
        "--input",
        required=True,
        help="path to the input v3 envelope JSON (or a JSON array of envelopes)",
    )
    p_export.add_argument(
        "--out",
        required=True,
        help="path to write the resulting JSONL file (or the base path when --ratios is given)",
    )
    p_export.add_argument(
        "--seed",
        default=42,
        type=int,
        help="splitter seed (default: 42)",
    )
    p_export.add_argument(
        "--ratios",
        default=None,
        help=(
            "comma-separated train,dev,test ratios summing to 1.0. "
            "When set, three files are written: <out>.train.jsonl, "
            "<out>.dev.jsonl, <out>.test.jsonl. Default: write all "
            "pairs to <out>."
        ),
    )
    p_export.add_argument(
        "--include-hard-negatives",
        action="store_true",
        help="generate synthetic hard negatives via the four documented strategies",
    )
    p_export.set_defaults(func=cmd_training_export_pairs)


__all__ = [
    "add_training_parser",
    "cli_training_export_pairs",
    "cmd_training_export_pairs",
]
