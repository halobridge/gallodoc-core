#!/usr/bin/env python3
"""Training recipe for gallodoc-bge-m3-v1.

Usage::

    python scripts/train_gallodoc_embedder.py \
        --pairs-train pairs.train.jsonl \
        --pairs-dev   pairs.dev.jsonl \
        --purpose     document_summary_embedding \
        --out         ./weights/gallodoc_bge_m3_v1 \
        --mode        standard

``--mode tiny`` is CPU-OK and runs on the synthetic fixtures in
``examples/v3_0/training/`` in seconds. It is the only mode CI exercises
and is the entry point Codex prompt 10's release demo calls. **It does
not write model weights** — that is deliberate; tiny mode is a dry run.

``--mode standard`` and ``--mode full`` lazy-import sentence_transformers
and a contrastive loss. The skeleton documents where the real training
loop plugs in but does not actually run training; this is the recipe,
not the model. Real training runs outside CI.

Decision 5 anchors the positives filter: positives must have a resolved
``semantic_intent`` on source AND target. Pairs lacking intent are
dropped from the positive set (counted in ``filtered_no_intent``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_VALID_MODES = ("tiny", "standard", "full")


def _now_iso() -> str:
    """ISO 8601 UTC timestamp, second precision, ``Z`` suffix."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file into a list of dicts. Empty file → empty list."""
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


@dataclass
class _FilteredCounts:
    """Counters reported in training_log.json after the Decision 5 sweep."""

    pairs_seen: int = 0
    positives_in: int = 0
    positives_kept: int = 0
    filtered_no_intent: int = 0
    negatives: int = 0
    uncertain: int = 0


def _decision_5_filter(
    pairs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], _FilteredCounts]:
    """Apply the Decision 5 positives filter and tally the buckets.

    Pairs with ``label == "match"`` and no ``semantic_intent`` are
    dropped from the positives set. Pairs with other labels pass through
    unchanged; the counts are split for the training log.
    """
    counts = _FilteredCounts(pairs_seen=len(pairs))
    kept: list[dict[str, Any]] = []
    for p in pairs:
        label = p.get("label")
        intent = p.get("semantic_intent")
        if label == "match":
            counts.positives_in += 1
            if isinstance(intent, str) and intent:
                counts.positives_kept += 1
                kept.append(p)
            else:
                counts.filtered_no_intent += 1
        elif label == "non_match":
            counts.negatives += 1
            kept.append(p)
        else:  # uncertain or anything else
            counts.uncertain += 1
            kept.append(p)
    return kept, counts


def _ensure_safety(pairs: list[dict[str, Any]]) -> None:
    """Run ``assert_no_enterprise_leakage`` on every pair.

    Imported lazily so the script's import surface stays minimal when
    the CLI just parses ``--help``.
    """
    from gallodoc.projection.safety import (  # noqa: PLC0415
        assert_no_enterprise_leakage,
    )

    for idx, p in enumerate(pairs):
        try:
            assert_no_enterprise_leakage(p)
        except Exception as exc:
            raise RuntimeError(
                f"training pair {idx} failed privacy scan: {exc}"
            ) from exc


def _write_training_log(
    out_dir: Path,
    purpose: str,
    mode: str,
    counts: _FilteredCounts,
    extra: dict[str, Any],
) -> Path:
    """Write ``<out>/<purpose>/training_log.json``."""
    head_dir = out_dir / purpose
    head_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "mode": mode,
        "purpose": purpose,
        "trained_at": _now_iso(),
        "epochs": extra.get("epochs", 0),
        "batch_size": extra.get("batch_size", 0),
        "base_model": extra.get("base_model", ""),
        "pairs_seen": counts.pairs_seen,
        "positives_in": counts.positives_in,
        "positives_kept": counts.positives_kept,
        "filtered_no_intent": counts.filtered_no_intent,
        "negatives": counts.negatives,
        "uncertain": counts.uncertain,
        "dummy_loss_final": extra.get("dummy_loss_final", 0.0),
        "notes": extra.get("notes", []),
    }
    log_path = head_dir / "training_log.json"
    log_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return log_path


def _run_tiny(
    pairs: list[dict[str, Any]],
    counts: _FilteredCounts,
    out_dir: Path,
    purpose: str,
    base_model: str,
) -> Path:
    """``--mode tiny`` — pipeline dry run with deterministic counters.

    Verifies pair-loading + Decision 5 filter + safety scan all work
    end-to-end. Computes a deterministic "dummy loss" (1.0 / (1 +
    positives_kept)) so the log carries a non-trivial value. **No model
    weights are written.**
    """
    epochs = 5
    batch_size = 4
    dummy_loss = 1.0 / (1.0 + float(counts.positives_kept))
    return _write_training_log(
        out_dir,
        purpose,
        mode="tiny",
        counts=counts,
        extra={
            "epochs": epochs,
            "batch_size": batch_size,
            "base_model": base_model,
            "dummy_loss_final": dummy_loss,
            "notes": [
                "tiny mode is a CI-only dry run. No weights are produced.",
                "standard / full modes plug the real training loop into "
                "this same orchestrator.",
                f"Decision 5: filtered_no_intent={counts.filtered_no_intent} "
                "positives dropped (intent missing on source or target).",
            ],
        },
    )


def _run_standard_or_full(
    pairs: list[dict[str, Any]],
    counts: _FilteredCounts,
    out_dir: Path,
    purpose: str,
    mode: str,
    base_model: str,
) -> Path:
    """``--mode standard`` / ``--mode full`` — skeleton with lazy heavy import.

    The body of the loop is documented but not executed here. This
    prompt ships the RECIPE, not the trained model. Users replace the
    body with the real training loop when running real training.
    """
    try:
        # Lazy heavy imports — fail fast if the [semantic] extra isn't
        # installed.
        import sentence_transformers  # noqa: F401, PLC0415
    except ImportError as exc:
        raise ImportError(
            "scripts/train_gallodoc_embedder.py "
            f"--mode {mode} requires sentence_transformers. "
            "Install via: pip install gallodoc[semantic]"
        ) from exc

    # --- REAL TRAINING LOOP PLUGS IN HERE ---------------------------
    # Sketch (not executed):
    #   model = SentenceTransformer(base_model)
    #   train_dataloader = build_pair_dataloader(pairs, batch_size=32)
    #   loss = sentence_transformers.losses.MultipleNegativesRankingLoss(model)
    #   model.fit(
    #       train_objectives=[(train_dataloader, loss)],
    #       epochs=20 if mode == "full" else 5,
    #       output_path=str(out_dir / purpose),
    #   )
    # ---------------------------------------------------------------

    epochs = 20 if mode == "full" else 5
    batch_size = 64 if mode == "full" else 32
    return _write_training_log(
        out_dir,
        purpose,
        mode=mode,
        counts=counts,
        extra={
            "epochs": epochs,
            "batch_size": batch_size,
            "base_model": base_model,
            "dummy_loss_final": 0.0,
            "notes": [
                f"{mode} mode skeleton — plug the real training loop where "
                "the comment marker is. This recipe ships open-source; "
                "real training runs are outside this repository.",
                "No weights have been written; see docs/training/lora_export.md "
                "for the expected output layout.",
            ],
        },
    )


def cli_train_gallodoc_embedder(
    pairs_train: str,
    pairs_dev: str | None,
    purpose: str,
    out: str,
    mode: str,
    base_model: str,
) -> int:
    """Library-form entry point used by tests.

    Returns ``0`` on success, non-zero on error. Errors are written to
    stderr.
    """
    if mode not in _VALID_MODES:
        sys.stderr.write(
            f"train_gallodoc_embedder: invalid --mode {mode!r}. "
            f"Allowed: {list(_VALID_MODES)}\n"
        )
        return 2

    # Validate purpose against PURPOSE_ENUM via lazy import.
    from gallodoc.semantic.embeddings.base import PURPOSE_ENUM  # noqa: PLC0415

    if purpose not in PURPOSE_ENUM:
        sys.stderr.write(
            f"train_gallodoc_embedder: invalid --purpose {purpose!r}. "
            f"Allowed: {sorted(PURPOSE_ENUM)}\n"
        )
        return 2

    train_path = Path(pairs_train)
    if not train_path.exists():
        sys.stderr.write(
            f"train_gallodoc_embedder: --pairs-train not found: {pairs_train}\n"
        )
        return 1

    try:
        pairs = _read_jsonl(train_path)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            f"train_gallodoc_embedder: failed to read --pairs-train: {exc}\n"
        )
        return 1

    # Optional dev set — read for side-effects (validation) only.
    if pairs_dev:
        dev_path = Path(pairs_dev)
        if not dev_path.exists():
            sys.stderr.write(
                f"train_gallodoc_embedder: --pairs-dev not found: {pairs_dev}\n"
            )
            return 1
        try:
            _ = _read_jsonl(dev_path)
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(
                f"train_gallodoc_embedder: failed to read --pairs-dev: {exc}\n"
            )
            return 1

    # Privacy guard FIRST so we never even bucket leaked content.
    try:
        _ensure_safety(pairs)
    except RuntimeError as exc:
        sys.stderr.write(f"train_gallodoc_embedder: {exc}\n")
        return 1

    kept_pairs, counts = _decision_5_filter(pairs)

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        if mode == "tiny":
            log_path = _run_tiny(
                kept_pairs, counts, out_dir, purpose, base_model
            )
        else:
            log_path = _run_standard_or_full(
                kept_pairs, counts, out_dir, purpose, mode, base_model
            )
    except ImportError as exc:
        sys.stderr.write(f"train_gallodoc_embedder: {exc}\n")
        return 1
    except OSError as exc:
        sys.stderr.write(
            f"train_gallodoc_embedder: failed to write training_log.json: {exc}\n"
        )
        return 1

    sys.stdout.write(
        f"wrote {log_path} (mode={mode}, purpose={purpose}, "
        f"pairs_seen={counts.pairs_seen}, "
        f"positives_kept={counts.positives_kept}, "
        f"filtered_no_intent={counts.filtered_no_intent})\n"
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="train_gallodoc_embedder",
        description="Training recipe for gallodoc-bge-m3-v1.",
    )
    p.add_argument(
        "--pairs-train",
        required=True,
        help="path to the training pairs JSONL (from gallodoc training export-pairs).",
    )
    p.add_argument(
        "--pairs-dev",
        default=None,
        help="optional path to a dev split JSONL (for early-stopping in real runs).",
    )
    p.add_argument(
        "--purpose",
        default="document_summary_embedding",
        help="purpose head to train (must be in PURPOSE_ENUM).",
    )
    p.add_argument(
        "--out",
        required=True,
        help="output directory for weights and training_log.json.",
    )
    p.add_argument(
        "--mode",
        default="standard",
        choices=list(_VALID_MODES),
        help="training mode. 'tiny' is CPU-OK and CI-friendly.",
    )
    p.add_argument(
        "--base-model",
        default="BAAI/bge-m3",
        help="HuggingFace id of the frozen base model.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return cli_train_gallodoc_embedder(
        pairs_train=args.pairs_train,
        pairs_dev=args.pairs_dev,
        purpose=args.purpose,
        out=args.out,
        mode=args.mode,
        base_model=args.base_model,
    )


if __name__ == "__main__":
    raise SystemExit(main())
