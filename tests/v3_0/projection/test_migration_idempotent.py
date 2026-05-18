"""migrate_v1_to_v3 is idempotent.

Required by the spec: running the migrator twice produces the same
result as one pass. Matters for safe pipeline retries and mixed-version
corpora where some envelopes are already partially migrated.
"""

from __future__ import annotations

from gallodoc.projection import migrate_v1_to_v3

from tests.v3_0.projection.conftest import (
    minimal_v1_envelope,
    v1_envelope_with_halobridge_block,
    v1_envelope_with_nested_trust,
)


def test_idempotent_on_minimal_v1() -> None:
    env = minimal_v1_envelope()
    first = migrate_v1_to_v3(env)
    second = migrate_v1_to_v3(first)
    assert first == second


def test_idempotent_with_nested_trust() -> None:
    env = v1_envelope_with_nested_trust()
    first = migrate_v1_to_v3(env)
    second = migrate_v1_to_v3(first)
    assert first == second


def test_idempotent_with_halobridge_promotion() -> None:
    env = v1_envelope_with_halobridge_block("consent_ledger", {"entries": [1, 2, 3]})
    first = migrate_v1_to_v3(env)
    second = migrate_v1_to_v3(first)
    assert first == second


def test_idempotent_with_double_emission() -> None:
    env = v1_envelope_with_halobridge_block(
        "attestations", {"marker": "ext-side", "version": "stale"}
    )
    env["attestations"] = {"marker": "top-level", "version": "canonical"}
    first = migrate_v1_to_v3(env)
    second = migrate_v1_to_v3(first)
    assert first == second
    assert first["attestations"]["marker"] == "top-level"
