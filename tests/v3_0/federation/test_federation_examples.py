"""Codex 08 — verify the committed federation examples.

The three input envelopes + three output envelopes in
``examples/v3_0/federation/`` are walkthrough fixtures. This test asserts:

- All six envelopes pass ``validate_envelope``.
- Running ``cross_tenant_link`` on the inputs reproduces the committed
  outputs (relationship_type, target, evidence-type count, receipt method).
  Timestamps are stabilized for committed artifacts.
- ``output_a_x_c.json`` has an empty ``matching_receipts`` list (tenant_c
  denies cross-tenant matching).
- Every matching receipt has ``raw_data_exposed: False`` (Rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

from gallodoc.federation import cross_tenant_link, build_matching_receipts
from gallodoc.linking import LinkerOutput
from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import EXAMPLES_DIR


_FED_DIR = EXAMPLES_DIR / "v3_0" / "federation"

_INPUT_FILES = (
    "tenant_a_envelope.json",
    "tenant_b_envelope.json",
    "tenant_c_envelope.json",
)

_OUTPUT_FILES = (
    "output_a_x_b.json",
    "output_a_x_c.json",
    "output_a_x_b_c.json",
)


def _load(name: str) -> dict:
    return json.loads((_FED_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_all_input_examples_validate() -> None:
    for name in _INPUT_FILES:
        env = _load(name)
        result = validate_envelope(env)
        assert result.valid, (
            f"{name}: validation failed — "
            f"{[(i.path, i.message) for i in result.errors()]}"
        )


def test_all_output_examples_validate() -> None:
    for name in _OUTPUT_FILES:
        env = _load(name)
        result = validate_envelope(env)
        assert result.valid, (
            f"{name}: validation failed — "
            f"{[(i.path, i.message) for i in result.errors()]}"
        )


# ---------------------------------------------------------------------------
# Output a × b — tenant_a fingerprint_only ∩ tenant_b trusted_exchange
# = fingerprint_only (more restrictive), one candidate, one receipt.
# ---------------------------------------------------------------------------


def test_output_a_x_b_matches_recomputed() -> None:
    src = _load("tenant_a_envelope.json")
    tgt = _load("tenant_b_envelope.json")
    committed = _load("output_a_x_b.json")

    linker_out = cross_tenant_link(src, [tgt])
    assert len(linker_out.candidates) == 1
    cand = linker_out.candidates[0]
    committed_rels = committed["relationships"]["relationships"]
    assert len(committed_rels) == 1
    expected = committed_rels[0]
    assert cand.target_document_id == expected["target_document_ref"]
    assert cand.relationship_type == expected["relationship_type"]
    assert cand.relationship_type in {"same_customer", "duplicate_of"}
    # Same number of evidence entries (post-filter)
    assert len(cand.relationship_evidence) == len(expected["relationship_evidence"])

    receipts = build_matching_receipts(src, tgt, linker_out)
    assert len(receipts) == 1
    assert receipts[0]["method"] == "fingerprint_only"
    assert receipts[0]["raw_data_exposed"] is False
    committed_receipts = committed["federation"]["matching_receipts"]
    assert len(committed_receipts) == 1
    assert committed_receipts[0]["method"] == receipts[0]["method"]


# ---------------------------------------------------------------------------
# Output a × c — tenant_c denies, empty results.
# ---------------------------------------------------------------------------


def test_output_a_x_c_has_no_candidates_or_receipts() -> None:
    committed = _load("output_a_x_c.json")
    assert committed["relationships"]["relationships"] == []
    assert committed["federation"]["matching_receipts"] == []

    # Recompute live for symmetry
    src = _load("tenant_a_envelope.json")
    tgt = _load("tenant_c_envelope.json")
    linker_out = cross_tenant_link(src, [tgt])
    assert linker_out.candidates == []
    assert build_matching_receipts(src, tgt, linker_out) == []


# ---------------------------------------------------------------------------
# Output a × [b, c] — only the tenant_b match survives.
# ---------------------------------------------------------------------------


def test_output_a_x_b_c_only_b_match_present() -> None:
    src = _load("tenant_a_envelope.json")
    tgt_b = _load("tenant_b_envelope.json")
    tgt_c = _load("tenant_c_envelope.json")

    linker_out = cross_tenant_link(src, [tgt_b, tgt_c])
    surviving_targets = {c.target_document_id for c in linker_out.candidates}
    assert surviving_targets == {"doc_tenant_b_invoice_002"}

    committed = _load("output_a_x_b_c.json")
    committed_targets = {
        r["target_document_ref"]
        for r in committed["relationships"]["relationships"]
    }
    assert committed_targets == surviving_targets


# ---------------------------------------------------------------------------
# Privacy invariant — every committed receipt has raw_data_exposed=False
# ---------------------------------------------------------------------------


def test_no_committed_receipt_has_raw_data_exposed_true() -> None:
    for name in _OUTPUT_FILES:
        env = _load(name)
        for i, r in enumerate(
            (env.get("federation") or {}).get("matching_receipts") or []
        ):
            assert r.get("raw_data_exposed") is False, (
                f"{name} matching_receipts[{i}] has raw_data_exposed={r.get('raw_data_exposed')!r} — must be False"
            )
