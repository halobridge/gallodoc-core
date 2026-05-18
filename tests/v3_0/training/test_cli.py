"""Tests for the ``gallodoc training export-pairs`` CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gallodoc.training.cli import cli_training_export_pairs


def _env_with_pair(
    *,
    gid: str = "doc_alpha",
    rel_id: str = "rel_001",
    status: str = "confirmed",
    discovered_by: str = "human_review",
    source_ref: str = "doc_alpha",
    target_ref: str = "doc_beta",
) -> dict[str, Any]:
    decisions = []
    if status in ("confirmed", "rejected"):
        decisions.append(
            {
                "decision_id": f"dec_{rel_id}",
                "relationship_id": rel_id,
                "verdict": status,
                "decided_by": "ap_lead@example.com",
                "decided_at": "2026-05-16T12:00:00Z",
            }
        )
    return {
        "schema_version": "gallodoc-core/v3",
        "identity": {"gallodoc_id": gid, "document_type": "invoice"},
        "source": {"source_system": "synthetic"},
        "gallounits": {"unit_strategy": "gallounit_v1", "units": []},
        "truth_ledger": {
            "available": False,
            "claims": [],
            "events": [],
            "truth_state": "uncertified",
        },
        "relationships": {
            "schema_version": "gallodoc.relationships.v3.0",
            "relationships": [
                {
                    "relationship_id": rel_id,
                    "source_document_ref": source_ref,
                    "target_document_ref": target_ref,
                    "relationship_type": "related_to",
                    "status": status,
                    "discovered_by": discovered_by,
                    "confidence": 0.9,
                }
            ],
            "relationship_decisions": decisions,
            "relationship_evidence": [],
        },
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_cli_export_pairs_on_envelope_writes_jsonl(tmp_path: Path) -> None:
    env = _env_with_pair()
    in_path = tmp_path / "env.json"
    in_path.write_text(json.dumps(env), encoding="utf-8")
    out_path = tmp_path / "pairs.jsonl"

    rc = cli_training_export_pairs(
        input_path=str(in_path),
        out_path=str(out_path),
        seed=42,
        ratios_str=None,
        include_hard_negatives=False,
    )
    assert rc == 0
    pairs = _read_jsonl(out_path)
    assert len(pairs) == 1
    assert pairs[0]["label"] == "match"


def test_cli_export_pairs_on_array_of_envelopes(tmp_path: Path) -> None:
    envs = [_env_with_pair(gid="d1", rel_id="r1"), _env_with_pair(gid="d2", rel_id="r2", source_ref="d2", target_ref="d3")]
    in_path = tmp_path / "envs.json"
    in_path.write_text(json.dumps(envs), encoding="utf-8")
    out_path = tmp_path / "pairs.jsonl"

    rc = cli_training_export_pairs(
        input_path=str(in_path),
        out_path=str(out_path),
        seed=42,
        ratios_str=None,
        include_hard_negatives=False,
    )
    assert rc == 0
    pairs = _read_jsonl(out_path)
    assert len(pairs) == 2


def test_cli_include_hard_negatives_appends_synthetic_pairs(tmp_path: Path) -> None:
    envs = [
        {
            "schema_version": "gallodoc-core/v3",
            "identity": {"gallodoc_id": "p1", "document_type": "employee_record"},
            "source": {"source_system": "hr"},
            "gallounits": {"unit_strategy": "gallounit_v1", "units": []},
            "truth_ledger": {"available": False, "claims": [], "events": [], "truth_state": "uncertified"},
            "relationships": {
                "schema_version": "gallodoc.relationships.v3.0",
                "relationships": [],
                "relationship_decisions": [],
                "relationship_evidence": [],
            },
        },
        {
            "schema_version": "gallodoc-core/v3",
            "identity": {"gallodoc_id": "p2", "document_type": "employee_record"},
            "source": {"source_system": "hr"},
            "gallounits": {"unit_strategy": "gallounit_v1", "units": []},
            "truth_ledger": {"available": False, "claims": [], "events": [], "truth_state": "uncertified"},
            "relationships": {
                "schema_version": "gallodoc.relationships.v3.0",
                "relationships": [],
                "relationship_decisions": [],
                "relationship_evidence": [],
            },
        },
    ]
    in_path = tmp_path / "envs.json"
    in_path.write_text(json.dumps(envs), encoding="utf-8")
    out_path = tmp_path / "pairs.jsonl"

    rc = cli_training_export_pairs(
        input_path=str(in_path),
        out_path=str(out_path),
        seed=42,
        ratios_str=None,
        include_hard_negatives=True,
    )
    assert rc == 0
    pairs = _read_jsonl(out_path)
    assert any(p["discovered_by"].startswith("hard_negative:") for p in pairs)


def test_cli_ratios_produces_three_files(tmp_path: Path) -> None:
    envs = [_env_with_pair(gid=f"d{i}", rel_id=f"r{i}", source_ref=f"src{i}", target_ref=f"tgt{i}") for i in range(40)]
    in_path = tmp_path / "envs.json"
    in_path.write_text(json.dumps(envs), encoding="utf-8")
    out_path = tmp_path / "pairs.jsonl"

    rc = cli_training_export_pairs(
        input_path=str(in_path),
        out_path=str(out_path),
        seed=42,
        ratios_str="0.8,0.1,0.1",
        include_hard_negatives=False,
    )
    assert rc == 0
    base = tmp_path / "pairs"
    assert (base.parent / "pairs.train.jsonl").exists()
    assert (base.parent / "pairs.dev.jsonl").exists()
    assert (base.parent / "pairs.test.jsonl").exists()
    total = (
        len(_read_jsonl(base.parent / "pairs.train.jsonl"))
        + len(_read_jsonl(base.parent / "pairs.dev.jsonl"))
        + len(_read_jsonl(base.parent / "pairs.test.jsonl"))
    )
    assert total == 40


def test_cli_bad_ratios_non_zero_exit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    env = _env_with_pair()
    in_path = tmp_path / "env.json"
    in_path.write_text(json.dumps(env), encoding="utf-8")
    out_path = tmp_path / "pairs.jsonl"

    rc = cli_training_export_pairs(
        input_path=str(in_path),
        out_path=str(out_path),
        seed=42,
        ratios_str="0.5,0.5,0.5",
        include_hard_negatives=False,
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert "must sum to 1.0" in err


def test_cli_missing_input_non_zero_exit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli_training_export_pairs(
        input_path=str(tmp_path / "no_such_file.json"),
        out_path=str(tmp_path / "out.jsonl"),
        seed=42,
        ratios_str=None,
        include_hard_negatives=False,
    )
    assert rc != 0
    assert "input not found" in capsys.readouterr().err


def test_cli_leak_in_input_non_zero_exit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    env = _env_with_pair(discovered_by="leak 123-45-6789")
    in_path = tmp_path / "env.json"
    in_path.write_text(json.dumps(env), encoding="utf-8")
    out_path = tmp_path / "pairs.jsonl"

    rc = cli_training_export_pairs(
        input_path=str(in_path),
        out_path=str(out_path),
        seed=42,
        ratios_str=None,
        include_hard_negatives=False,
    )
    assert rc != 0
    assert "privacy scan failed" in capsys.readouterr().err
