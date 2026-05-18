"""Deterministic train/dev/test splitter for training pairs.

See ``docs/specs/gallodoc-core-v3-training-lab.md`` §5.

Implementation: hash ``f"{pair_id}::{seed}"`` with sha256, take the
result modulo 1000, and assign to a bucket. Buckets ``[0, train_cap)``
go to ``train``, ``[train_cap, dev_cap)`` go to ``dev``, the remainder
go to ``test``. This guarantees the same pair always lands in the same
split across runs and across input orderings.
"""

from __future__ import annotations

import hashlib

from gallodoc.training.pairs import TrainingPair


def split_train_dev_test(
    pairs: list[TrainingPair],
    *,
    seed: int = 42,
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
) -> dict[str, list[TrainingPair]]:
    """Deterministic train/dev/test split.

    Parameters
    ----------
    pairs:
        Pairs to partition.
    seed:
        Salt mixed into the per-pair hash. Different seeds yield
        different partitions (with high probability) on the same input.
    ratios:
        ``(train, dev, test)`` floats. Must sum to 1.0 (±1e-6) and be
        non-negative. Defaults to ``(0.8, 0.1, 0.1)``.

    Returns
    -------
    A dict with keys ``"train"``, ``"dev"``, ``"test"`` mapping to lists
    of pairs (each list preserves input ordering).
    """
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0, got {ratios} = {sum(ratios)}")
    if any(r < 0 for r in ratios):
        raise ValueError(f"ratios must be non-negative, got {ratios}")

    train_cap = int(1000 * ratios[0])
    dev_cap = train_cap + int(1000 * ratios[1])

    out: dict[str, list[TrainingPair]] = {"train": [], "dev": [], "test": []}
    for p in pairs:
        key = f"{p.pair_id}::{seed}".encode("utf-8")
        bucket = int(hashlib.sha256(key).hexdigest(), 16) % 1000
        if bucket < train_cap:
            out["train"].append(p)
        elif bucket < dev_cap:
            out["dev"].append(p)
        else:
            out["test"].append(p)
    return out


__all__ = ["split_train_dev_test"]
