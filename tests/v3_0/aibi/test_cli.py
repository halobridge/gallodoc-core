"""Tests for the ``gallodoc aibi plan`` CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gallodoc.aibi.cli import cli_aibi_plan


def test_cli_recognized_nl_emits_plan(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli_aibi_plan(
        nl="show invoices linked to John",
        envelope_path=None,
        check_only=False,
        out_path=None,
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["safe_query_type"] == "relationship_query"
    assert payload["plan_id"].startswith("plan_")


def test_cli_check_only_does_not_write(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_path = tmp_path / "plan.json"
    rc = cli_aibi_plan(
        nl="show invoices linked to John",
        envelope_path=None,
        check_only=True,
        out_path=str(out_path),
    )
    assert rc == 0
    assert not out_path.exists()
    out = capsys.readouterr().out
    assert "OK" in out


def test_cli_unrecognized_nl_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli_aibi_plan(
        nl="the quick brown fox jumps over the lazy dog",
        envelope_path=None,
        check_only=False,
        out_path=None,
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert "planner error" in err


def test_cli_sql_in_nl_blocked(capsys: pytest.CaptureFixture[str]) -> None:
    # NL like "show invoices linked to SELECT * FROM users" — the planner
    # will match the relationship template on "linked to" and put the SQL
    # text into the user_intent_summary / filter value. The safety scan
    # must catch it.
    rc = cli_aibi_plan(
        nl="show invoices linked to SELECT * FROM users",
        envelope_path=None,
        check_only=False,
        out_path=None,
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert "unsafe plan" in err


def test_cli_write_to_file(tmp_path: Path) -> None:
    out_path = tmp_path / "plan.json"
    rc = cli_aibi_plan(
        nl="show invoices linked to John",
        envelope_path=None,
        check_only=False,
        out_path=str(out_path),
    )
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["safe_query_type"] == "relationship_query"


def test_cli_envelope_path_loaded(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    envelope = {
        "schema_version": "gallodoc-core/v3",
        "federation": {
            "cross_tenant_policy": {
                "allowed": True,
                "sharing_scope": "fingerprint_only",
            },
        },
    }
    envelope_path = tmp_path / "envelope.json"
    envelope_path.write_text(json.dumps(envelope), encoding="utf-8")

    rc = cli_aibi_plan(
        nl="show invoices linked to John across tenants",
        envelope_path=str(envelope_path),
        check_only=False,
        out_path=None,
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    # cross-tenant federation_intersection check should appear
    checks = [c["check"] for c in payload["policy_checks"]]
    assert "federation_intersection" in checks
