"""project_to_open_core is idempotent.

Running the projector twice produces the same result as one pass.
This is required for safe pipeline retries and for mixed-version
corpora where some envelopes are already partially sanitized.
"""

from __future__ import annotations

from gallodoc.projection import project_to_open_core

from tests.v3_0.projection.conftest import minimal_v3_envelope


def test_idempotent_on_minimal_v3() -> None:
    env = minimal_v3_envelope()
    first = project_to_open_core(env)
    second = project_to_open_core(first)
    assert first == second


def test_idempotent_on_envelope_with_optional_blocks() -> None:
    env = minimal_v3_envelope()
    env["consent_ledger"] = {"schema_version": "gallodoc.consent_ledger.v1.2", "entries": []}
    env["attestations"] = {"schema_version": "gallodoc.attestations.v1.2", "attestations": []}
    env["federation"] = {"available": False}
    first = project_to_open_core(env)
    second = project_to_open_core(first)
    assert first == second
    # Sanity: optional blocks survived the projection.
    assert first.get("consent_ledger") is not None
    assert first.get("federation") is not None


def test_idempotent_on_non_dict_input() -> None:
    # The projector returns a fallback envelope; projecting that again is a no-op.
    first = project_to_open_core(None)  # type: ignore[arg-type]
    second = project_to_open_core(first)
    assert first == second
    assert first["schema_version"] == "gallodoc-core/v3"
