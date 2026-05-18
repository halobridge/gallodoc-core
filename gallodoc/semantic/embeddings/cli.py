"""CLI dispatch for ``gallodoc semantic embed ...``.

The ``gallodoc`` binary in ``gallodoc/cli/main.py`` wires ``semantic``
as a top-level subcommand. This module owns the dispatch logic so the
binary stays small and the embeddings machinery stays inside
``gallodoc.semantic.embeddings``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def cli_semantic_embed(
    input_path: str,
    adapter_name: str,
    purpose: str,
    out_path: str,
    include_vector: bool,
) -> int:
    """Embed an envelope's gallounits and write the result to ``out_path``.

    Returns ``0`` on success, non-zero on bad slug / bad purpose /
    missing input / write error / unauthorized ``--include-vector``.
    Stderr carries the human-readable error message.
    """
    # Late import to keep stdlib-only path fast for unrelated CLI calls.
    from gallodoc.semantic.embeddings import (  # noqa: PLC0415
        EMBEDDING_ADAPTERS,
        PURPOSE_ENUM,
        apply_embeddings,
    )
    from gallodoc.projection.safety import EnterpriseLeakageError  # noqa: PLC0415

    adapter_cls = EMBEDDING_ADAPTERS.get(adapter_name)
    if adapter_cls is None:
        sys.stderr.write(
            f"gallodoc semantic embed: unknown adapter "
            f"{adapter_name!r}. Available: {sorted(EMBEDDING_ADAPTERS)}\n"
        )
        return 1

    if purpose not in PURPOSE_ENUM:
        sys.stderr.write(
            f"gallodoc semantic embed: unknown purpose {purpose!r}. "
            f"Allowed: {sorted(PURPOSE_ENUM)}\n"
        )
        return 1

    src = Path(input_path)
    if not src.exists():
        sys.stderr.write(
            f"gallodoc semantic embed: input not found: {input_path}\n"
        )
        return 1

    try:
        envelope = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"gallodoc semantic embed: failed to parse input as JSON: {exc}\n"
        )
        return 1

    try:
        adapter = adapter_cls()
    except Exception as exc:  # pragma: no cover — defensive
        sys.stderr.write(
            f"gallodoc semantic embed: adapter instantiation failed: {exc}\n"
        )
        return 1

    try:
        result = apply_embeddings(
            envelope,
            adapter,
            purpose,
            include_vector=include_vector,
        )
    except EnterpriseLeakageError as exc:
        sys.stderr.write(f"gallodoc semantic embed: {exc}\n")
        return 1
    except ValueError as exc:
        # Defensive — purpose was already validated above, but
        # apply_embeddings re-validates internally.
        sys.stderr.write(f"gallodoc semantic embed: {exc}\n")
        return 1
    except Exception as exc:  # pragma: no cover — defensive
        sys.stderr.write(f"gallodoc semantic embed: embed failed: {exc}\n")
        return 1

    try:
        Path(out_path).write_text(
            json.dumps(result, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        sys.stderr.write(
            f"gallodoc semantic embed: failed to write {out_path}: {exc}\n"
        )
        return 1

    n = len((result.get("gallounits") or {}).get("embeddings") or [])
    sys.stdout.write(
        f"wrote {out_path} ({n} embedding"
        + ("s" if n != 1 else "")
        + ", adapter={}, purpose={})\n".format(adapter_name, purpose)
    )
    return 0


def cmd_semantic_embed(args: argparse.Namespace) -> int:
    """argparse-facing wrapper around ``cli_semantic_embed``."""
    return cli_semantic_embed(
        input_path=args.input,
        adapter_name=args.adapter,
        purpose=args.purpose,
        out_path=args.out,
        include_vector=bool(args.include_vector),
    )


def add_semantic_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``semantic`` subcommand on the main argparser."""
    p_semantic = subparsers.add_parser(
        "semantic",
        help="Semantic commands (embed gallounits with an EmbeddingAdapter).",
    )
    semantic_sub = p_semantic.add_subparsers(
        dest="semantic_command", required=True
    )

    p_embed = semantic_sub.add_parser(
        "embed",
        help="Embed gallounits in a v3 envelope using a named adapter.",
    )
    p_embed.add_argument(
        "input",
        help="path to the input v3 envelope JSON file",
    )
    p_embed.add_argument(
        "--adapter",
        default="local_stub",
        help="adapter slug (local_stub, bge_m3, sentence_transformers). "
        "Default: local_stub.",
    )
    p_embed.add_argument(
        "--purpose",
        default="document_summary_embedding",
        help="embedding purpose (one of the closed PURPOSE_ENUM values). "
        "Default: document_summary_embedding.",
    )
    p_embed.add_argument(
        "--out",
        required=True,
        help="path to write the resulting embedded envelope JSON",
    )
    p_embed.add_argument(
        "--include-vector",
        action="store_true",
        help="ship raw vector floats inline. Requires "
        "safety_profile.raw_vectors_stored=true on the input envelope.",
    )
    p_embed.set_defaults(func=cmd_semantic_embed)


__all__ = [
    "cli_semantic_embed",
    "cmd_semantic_embed",
    "add_semantic_parser",
]
