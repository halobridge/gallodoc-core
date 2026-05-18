"""Walk-through reproducibility test for ``examples/v3_0/training/``.

Re-runs the exporter pipeline on the committed ``input_envelopes.json``
and asserts byte-equality with the committed output JSONL files,
modulo the timestamp-stamped ``created_at`` field.
"""

from __future__ import annotations

import json
from pathlib import Path

from gallodoc.training import (
    extract_pairs_from_envelopes,
    generate_hard_negatives,
    split_train_dev_test,
)


_EXAMPLES_DIR = (
    Path(__file__).resolve().parents[3] / "examples" / "v3_0" / "training"
)
_STABLE_TS = "2026-05-16T12:00:00Z"


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _to_dicts(pairs) -> list[dict]:
    out = []
    for p in pairs:
        # Stabilize the timestamp so the test is reproducible.
        d = p.to_dict()
        d["created_at"] = _STABLE_TS
        out.append(d)
    return out


def _load_input() -> list[dict]:
    with (_EXAMPLES_DIR / "input_envelopes.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def test_basic_pairs_match_committed_example() -> None:
    envelopes = _load_input()
    pairs = extract_pairs_from_envelopes(envelopes)
    actual = _to_dicts(pairs)
    expected = _load_jsonl(_EXAMPLES_DIR / "output_pairs.jsonl")
    assert actual == expected


def test_pairs_with_hard_negatives_match_committed_example() -> None:
    envelopes = _load_input()
    pairs = extract_pairs_from_envelopes(envelopes)
    pairs.extend(generate_hard_negatives(envelopes))
    actual = _to_dicts(pairs)
    expected = _load_jsonl(
        _EXAMPLES_DIR / "output_pairs_with_hard_negatives.jsonl"
    )
    assert actual == expected


def test_split_matches_committed_examples() -> None:
    envelopes = _load_input()
    pairs = extract_pairs_from_envelopes(envelopes)
    splits = split_train_dev_test(pairs, seed=42)
    for name in ("train", "dev", "test"):
        actual = _to_dicts(splits[name])
        expected_path = _EXAMPLES_DIR / f"output_pairs.{name}.jsonl"
        expected = _load_jsonl(expected_path) if expected_path.read_text(encoding="utf-8") else []
        assert actual == expected, f"{name} split mismatch"


def test_linker_confirmed_positive_is_in_committed_basic_output() -> None:
    """Locks in the load-bearing Decision 3 invariant on disk."""
    pairs = _load_jsonl(_EXAMPLES_DIR / "output_pairs.jsonl")
    linker_positives = [
        p
        for p in pairs
        if p["label"] == "match"
        and "linker" in p["discovered_by"].lower()
    ]
    assert linker_positives, "expected at least one linker-confirmed positive"


def test_all_four_hard_negative_strategies_fired() -> None:
    pairs = _load_jsonl(
        _EXAMPLES_DIR / "output_pairs_with_hard_negatives.jsonl"
    )
    strategies = {
        p["discovered_by"].split(":", 1)[1]
        for p in pairs
        if p["discovered_by"].startswith("hard_negative:")
    }
    assert strategies == {
        "same_org_wrong_person",
        "same_vendor_wrong_invoice",
        "similar_clause_different_obligation",
        "same_customer_name_different_domain",
    }


def test_splits_sum_equals_basic_output_count() -> None:
    basic = _load_jsonl(_EXAMPLES_DIR / "output_pairs.jsonl")
    train = _load_jsonl(_EXAMPLES_DIR / "output_pairs.train.jsonl")
    dev_path = _EXAMPLES_DIR / "output_pairs.dev.jsonl"
    test = _load_jsonl(_EXAMPLES_DIR / "output_pairs.test.jsonl")
    dev = _load_jsonl(dev_path) if dev_path.read_text(encoding="utf-8") else []
    assert len(train) + len(dev) + len(test) == len(basic)
