"""Codex 08 — gallodoc federation match CLI subcommand."""

from __future__ import annotations

import json
from pathlib import Path

from gallodoc.cli.main import main as cli_main
from gallodoc.federation.cli import cli_federation_match
from gallodoc.validation import validate_envelope

from tests.v3_0.conftest import minimal_v3_envelope


_SHARED_HASH = "sha256:" + "a" * 64


def _src_envelope(*, federation_policy: dict | None = None) -> dict:
    env = minimal_v3_envelope()
    env["identity"]["gallodoc_id"] = "doc_src"
    env["gallounits"]["units"] = [{"unit_id": "u1", "text_hash": _SHARED_HASH}]
    if federation_policy is not None:
        env["federation"] = {
            "schema_version": "gallodoc.federation.v3.0",
            "tenant_id_hash": "sha256:" + "a" * 64,
            "cross_tenant_policy": federation_policy,
        }
    return env


def _tgt_envelope(
    gallodoc_id: str, *, federation_policy: dict | None = None
) -> dict:
    env = minimal_v3_envelope()
    env["identity"]["gallodoc_id"] = gallodoc_id
    env["gallounits"]["units"] = [{"unit_id": "u2", "text_hash": _SHARED_HASH}]
    if federation_policy is not None:
        env["federation"] = {
            "schema_version": "gallodoc.federation.v3.0",
            "tenant_id_hash": "sha256:" + "b" * 64,
            "cross_tenant_policy": federation_policy,
        }
    return env


_ALLOW = {
    "allowed": True,
    "sharing_scope": "trusted_exchange",
    "raw_data_visible": False,
    "fingerprint_sharing_allowed": True,
    "embedding_sharing_allowed": True,
    "requires_review": False,
    "permitted_relationship_types": [],
}


# ---------------------------------------------------------------------------
# cli_federation_match — direct function tests
# ---------------------------------------------------------------------------


def test_cli_federation_match_populates_receipts(tmp_path: Path) -> None:
    src = _src_envelope(federation_policy=_ALLOW)
    tgt = _tgt_envelope("doc_tgt", federation_policy=_ALLOW)
    src_path = tmp_path / "src.json"
    tgts_path = tmp_path / "targets.json"
    out_path = tmp_path / "out.json"
    src_path.write_text(json.dumps(src), encoding="utf-8")
    tgts_path.write_text(json.dumps([tgt]), encoding="utf-8")

    env = cli_federation_match(
        source_path=str(src_path),
        targets_spec=str(tgts_path),
        out_path=str(out_path),
    )
    # Output file matches return value
    assert out_path.exists()
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert on_disk["federation"]["matching_receipts"] == env["federation"]["matching_receipts"]

    receipts = env["federation"]["matching_receipts"]
    assert len(receipts) >= 1
    for r in receipts:
        assert r["raw_data_exposed"] is False


def test_cli_federation_match_no_federation_block_defaults_to_tenant_private(
    tmp_path: Path,
) -> None:
    """When the source has no federation block, defaults yield empty receipts."""
    src = _src_envelope(federation_policy=None)
    tgt = _tgt_envelope("doc_tgt", federation_policy=_ALLOW)
    src_path = tmp_path / "src.json"
    tgts_path = tmp_path / "targets.json"
    out_path = tmp_path / "out.json"
    src_path.write_text(json.dumps(src), encoding="utf-8")
    tgts_path.write_text(json.dumps([tgt]), encoding="utf-8")

    env = cli_federation_match(
        source_path=str(src_path),
        targets_spec=str(tgts_path),
        out_path=str(out_path),
    )
    # Federation block ends up populated (with an empty receipts list) so the
    # output envelope is well-formed.
    assert (env.get("federation") or {}).get("matching_receipts") == []


def test_cli_federation_match_output_validates(tmp_path: Path) -> None:
    src = _src_envelope(federation_policy=_ALLOW)
    tgt = _tgt_envelope("doc_tgt", federation_policy=_ALLOW)
    src_path = tmp_path / "src.json"
    tgts_path = tmp_path / "targets.json"
    out_path = tmp_path / "out.json"
    src_path.write_text(json.dumps(src), encoding="utf-8")
    tgts_path.write_text(json.dumps([tgt]), encoding="utf-8")

    env = cli_federation_match(
        source_path=str(src_path),
        targets_spec=str(tgts_path),
        out_path=str(out_path),
    )
    result = validate_envelope(env)
    assert result.valid, (
        f"federation-CLI output envelope should validate: "
        f"{[(i.path, i.message) for i in result.errors()]}"
    )


def test_cli_federation_match_glob_loads_multiple_targets(tmp_path: Path) -> None:
    """Glob expansion loads one envelope per matched file."""
    src = _src_envelope(federation_policy=_ALLOW)
    src_path = tmp_path / "src.json"
    src_path.write_text(json.dumps(src), encoding="utf-8")
    tgt_a = _tgt_envelope("doc_tgt_a", federation_policy=_ALLOW)
    tgt_b = _tgt_envelope("doc_tgt_b", federation_policy=_ALLOW)
    (tmp_path / "tgt_a.json").write_text(json.dumps(tgt_a), encoding="utf-8")
    (tmp_path / "tgt_b.json").write_text(json.dumps(tgt_b), encoding="utf-8")
    out_path = tmp_path / "out.json"

    env = cli_federation_match(
        source_path=str(src_path),
        targets_spec=str(tmp_path / "tgt_*.json"),
        out_path=str(out_path),
    )
    # Both candidates should survive (both targets allow trusted_exchange).
    rels = (env.get("relationships") or {}).get("relationships") or []
    targets_seen = {r.get("target_document_ref") for r in rels}
    assert targets_seen == {"doc_tgt_a", "doc_tgt_b"}


# ---------------------------------------------------------------------------
# CLI argparse entrypoint
# ---------------------------------------------------------------------------


def test_cli_main_dispatch_returns_zero(tmp_path: Path) -> None:
    src = _src_envelope(federation_policy=_ALLOW)
    tgt = _tgt_envelope("doc_tgt", federation_policy=_ALLOW)
    src_path = tmp_path / "src.json"
    tgts_path = tmp_path / "targets.json"
    out_path = tmp_path / "out.json"
    src_path.write_text(json.dumps(src), encoding="utf-8")
    tgts_path.write_text(json.dumps([tgt]), encoding="utf-8")

    rc = cli_main(
        [
            "federation",
            "match",
            "--source",
            str(src_path),
            "--targets",
            str(tgts_path),
            "--out",
            str(out_path),
            "--json",
        ]
    )
    assert rc == 0
    assert out_path.exists()
