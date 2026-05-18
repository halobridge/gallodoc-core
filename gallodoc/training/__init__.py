"""GalloDoc embedder training lab.

Open-source pipeline that turns human-curated v3 envelopes into a JSONL
training set the prompt 07 embedder consumes. Implementation lives in
this package; the CLI is wired through ``gallodoc.cli.main``.

See ``docs/specs/gallodoc-core-v3-training-lab.md`` for the spec.
"""

from gallodoc.training.exporter import (
    extract_pairs_from_envelope,
    extract_pairs_from_envelopes,
)
from gallodoc.training.hard_negatives import STRATEGIES, generate_hard_negatives
from gallodoc.training.pairs import LABEL_ENUM, TrainingPair
from gallodoc.training.safety import assert_pairs_clean
from gallodoc.training.splitter import split_train_dev_test


__all__ = [
    "LABEL_ENUM",
    "STRATEGIES",
    "TrainingPair",
    "assert_pairs_clean",
    "extract_pairs_from_envelope",
    "extract_pairs_from_envelopes",
    "generate_hard_negatives",
    "split_train_dev_test",
]
