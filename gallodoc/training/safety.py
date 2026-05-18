"""Privacy safety scan over a list of training pairs.

Every exported pair must pass ``assert_no_enterprise_leakage`` (Codex 02)
before it ships. There is no skip path and no ``--unsafe`` flag — the
export aborts on the first leak.

See ``docs/specs/gallodoc-core-v3-training-lab.md`` §6.
"""

from __future__ import annotations

from gallodoc.projection.safety import (
    EnterpriseLeakageError,
    assert_no_enterprise_leakage,
)
from gallodoc.training.pairs import TrainingPair


def assert_pairs_clean(pairs: list[TrainingPair]) -> None:
    """Raise :class:`EnterpriseLeakageError` on the first leaking pair.

    Each pair is converted to its dict form and walked by
    ``assert_no_enterprise_leakage``. The raised error message includes
    the zero-based pair index that tripped the scan, plus a short
    fingerprint of the offending pair (``pair_id``) for triage.
    """
    for idx, p in enumerate(pairs):
        try:
            assert_no_enterprise_leakage(p.to_dict())
        except EnterpriseLeakageError as exc:
            raise EnterpriseLeakageError(
                f"training pair {idx} ({p.pair_id!r}) failed privacy scan: {exc}"
            ) from exc


__all__ = ["assert_pairs_clean"]
