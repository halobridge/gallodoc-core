"""Migration transform 2 — relationship status + discovered_by injection.

Per Decision 3, every entry in a v1 `relationships` array gets
`status: "confirmed"` and `discovered_by: "v1_migration"` if missing.
Existing values are preserved.
"""

from __future__ import annotations

from gallodoc.projection import migrate_v1_to_v3

from tests.v3_0.projection.conftest import minimal_v1_envelope


def test_bare_list_relationships_become_v3_object_shape() -> None:
    env = minimal_v1_envelope()
    env["relationships"] = [
        {"relationship_id": "r1", "relationship_type": "supports"},
    ]
    out = migrate_v1_to_v3(env)
    assert isinstance(out["relationships"], dict)
    assert isinstance(out["relationships"]["relationships"], list)
    assert len(out["relationships"]["relationships"]) == 1


def test_missing_status_defaults_to_confirmed() -> None:
    env = minimal_v1_envelope()
    env["relationships"] = [{"relationship_id": "r1", "relationship_type": "supports"}]
    out = migrate_v1_to_v3(env)
    rel = out["relationships"]["relationships"][0]
    assert rel["status"] == "confirmed"


def test_missing_discovered_by_defaults_to_v1_migration() -> None:
    env = minimal_v1_envelope()
    env["relationships"] = [{"relationship_id": "r1", "relationship_type": "supports"}]
    out = migrate_v1_to_v3(env)
    rel = out["relationships"]["relationships"][0]
    assert rel["discovered_by"] == "v1_migration"


def test_existing_status_not_overwritten() -> None:
    env = minimal_v1_envelope()
    env["relationships"] = [
        {"relationship_id": "r1", "relationship_type": "supports", "status": "rejected"},
    ]
    out = migrate_v1_to_v3(env)
    rel = out["relationships"]["relationships"][0]
    assert rel["status"] == "rejected"  # preserved
    assert rel["discovered_by"] == "v1_migration"  # injected (was missing)


def test_existing_discovered_by_not_overwritten() -> None:
    env = minimal_v1_envelope()
    env["relationships"] = [
        {
            "relationship_id": "r1",
            "relationship_type": "supports",
            "discovered_by": "gallodoc-linker/2.0",
        },
    ]
    out = migrate_v1_to_v3(env)
    rel = out["relationships"]["relationships"][0]
    # Status was missing — injected.
    assert rel["status"] == "confirmed"
    # discovered_by was set — preserved.
    assert rel["discovered_by"] == "gallodoc-linker/2.0"


def test_multiple_relationships_all_injected() -> None:
    env = minimal_v1_envelope()
    env["relationships"] = [
        {"relationship_id": "r1", "relationship_type": "supports"},
        {"relationship_id": "r2", "relationship_type": "contradicts"},
        {"relationship_id": "r3", "relationship_type": "supersedes", "status": "rejected"},
    ]
    out = migrate_v1_to_v3(env)
    entries = out["relationships"]["relationships"]
    assert entries[0]["status"] == "confirmed"
    assert entries[1]["status"] == "confirmed"
    assert entries[2]["status"] == "rejected"
    for entry in entries:
        assert "discovered_by" in entry


def test_v2_object_shape_relationships_also_get_injection() -> None:
    """If the input is already v2.0 object-shaped, the migrator still injects defaults."""
    env = minimal_v1_envelope()
    env["relationships"] = {
        "relationships": [
            {"relationship_id": "r1", "relationship_type": "supports"},
        ]
    }
    out = migrate_v1_to_v3(env)
    rel = out["relationships"]["relationships"][0]
    assert rel["status"] == "confirmed"
    assert rel["discovered_by"] == "v1_migration"
