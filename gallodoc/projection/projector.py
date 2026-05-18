"""Open-source reference projector for ``gallodoc-core/v3`` envelopes.

``project_to_open_core`` is the field-stripping + cardinality-capping +
enum-coercing entry point. It never raises; it returns a v3-shaped
envelope no matter how malformed the input is.

This is the open-source reference. The HaloBridge platform projector
wraps it and layers platform-specific stripping (``policy_formula``,
``halobridge_internal``, ``__internal__``) on top — those patterns are
NOT stripped here. See
``docs/specs/gallodoc-core-v3-reference-projector.md`` for the layering
contract.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from gallodoc.projection.forbidden import EXTENSIONS_HALOBRIDGE_BANNED


# Maximum recursion depth — defensive cap for cyclic-or-deeply-nested input.
_MAX_DEPTH = 16

# Maximum array cardinality per list — matches the validator's `[:512]`
# slice pattern in ``gallodoc.validation._scan_v20_block_leaks``.
_MAX_ARRAY = 512

# Open-source-known forbidden key names. Mirrors the union of the
# validator's per-block forbidden sets. The platform-private patterns
# (``policy_formula``, ``halobridge_internal``, ``__internal__``) are
# deliberately NOT included — they belong to the platform projector.
#
# Names are lowercased for case-insensitive matching against incoming
# keys (the validator's matching helpers also lower-case before lookup).
_FORBIDDEN_KEY_NAMES: frozenset[str] = frozenset({
    # v1.1 execution governance
    "prompt_text",
    "raw_prompt",
    "raw_response",
    "response_text",
    "phi",
    "patient_id",
    "mrn",
    "access_token",
    "refresh_token",
    "oauth_token",
    "id_token",
    "bearer_token",
    "authorization",
    "client_secret",
    "api_key",
    "secret",
    "private_key",
    "ip_hash",
    "session_hash",
    "jwt",
    "jwk",
    # v1.2 compliance extras
    "raw_signature",
    "signature_blob",
    "patient_name",
    "passport_number",
    "drivers_license",
    "street_address",
    "phone_number",
    "fax_number",
    # v1.3 compliance extras
    "training_payload",
    "fine_tune_dataset",
    "training_batch",
    "model_weights",
    "lora_weights",
    "adapter_blob",
    "gradient_checkpoint",
    # v1.4 compliance extras
    "chain_of_thought",
    "cot_trace",
    "hidden_reasoning",
    "thought_chain",
    "scratchpad",
    "retrieval_chunk_body",
    "phi_chunk",
    "tool_parameters",
    "raw_sql_text",
    # v1.5 trust_decision extras
    "raw_phi",
    "proprietary_weights",
    "formula_weights",
    "scoring_weight_matrix",
    "tenant_internals",
    # v1.6 agent_supply_chain extras
    "secret_value",
    "credential_value",
    "credential_dump",
    "raw_environment",
    "environment_variables",
    "env_vars",
    "raw_file_body",
    "source_code",
    "executable_payload",
    "binary_payload",
    "host_output",
    "sandbox_stdout",
    "sandbox_stderr",
    "network_capture",
    "packet_capture",
    # v2.0 base
    "raw_secret",
    "plaintext_secret",
    "raw_code",
    "ssn",
    "dob",
    "tenant_id",
    "password",
    # v2.0 per-block extras
    "raw_sql",
    "sql_text",
    "sql_query",
    "raw_query",
    "raw_dialect_query",
    "raw_vector",
    "embedding_vector",
    "vector_payload",
    "raw_embedding",
    "chunk_text",
    "raw_chunk_text",
    "raw_field_value",
    "field_value",
    "raw_match_text",
    "raw_before",
    "raw_after",
    "before_value",
    "after_value",
    "raw_diff",
    "diff_text",
    "raw_policy_body",
    "rego_source",
    "policy_source",
    "rule_body",
    "raw_rule_body",
    "user_id",
    "user_email",
    "user_name",
    "actor_id",
    "actor_email",
    "actor_name",
    "raw_notes",
    "reviewer_id",
    "reviewer_email",
    "reviewer_name",
    "notes_body",
    "reviewer_user_id",
    "raw_input",
    "raw_output",
    "input_payload",
    "output_payload",
    "stack_trace",
    "raw_stack_trace",
    "raw_url",
    "raw_endpoint",
    "raw_record",
    "record_payload",
    "credential",
    "auth_credential",
    "raw_log",
    "log_body",
    "raw_message",
    "raw_metric_values",
    "advisory_body",
    "raw_advisory",
    "exploit_payload",
    "malware_payload",
})


# v3 relationship status enum (Decision 3). Invalid values coerce to "suggested".
_RELATIONSHIP_STATUS_ENUM: frozenset[str] = frozenset({"suggested", "confirmed", "rejected"})

# Discovered-by detector — linker-discovered relationships must pin to
# ``suggested`` per Decision 3.
_DISCOVERED_BY_LINKER_RE = re.compile(r".*linker.*", re.IGNORECASE)


def _is_forbidden_key(key: Any) -> bool:
    """True iff ``key`` is one of the open-source-known forbidden names."""
    if not isinstance(key, str):
        return False
    return key.strip().lower() in _FORBIDDEN_KEY_NAMES


def _strip(value: Any, *, depth: int = 0) -> Any:
    """Recursively strip forbidden keys + cap array cardinality.

    Returns a freshly-constructed structure — does not mutate the input.
    Does NOT strip the platform-specific patterns
    (``policy_formula``, ``halobridge_internal``, ``__internal__``);
    those stay in the output for the platform projector to handle.
    """
    if depth > _MAX_DEPTH:
        # Defensive: collapse to a string so the caller doesn't crash on
        # cyclic input. Functionally unreachable in normal envelopes.
        return None
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if _is_forbidden_key(k):
                continue
            out[k] = _strip(v, depth=depth + 1)
        return out
    if isinstance(value, list):
        return [_strip(item, depth=depth + 1) for item in value[:_MAX_ARRAY]]
    return value


def _strip_banned_halobridge(envelope: dict[str, Any]) -> None:
    """Remove ``extensions.halobridge.<name>`` keys in EXTENSIONS_HALOBRIDGE_BANNED.

    Mutates ``envelope`` in place. If ``extensions.halobridge`` becomes
    empty, drop the ``halobridge`` key. If ``extensions`` becomes empty,
    drop ``extensions`` itself (or leave an empty dict — the v3 schema
    requires ``extensions`` to be present, so we leave it as ``{}``).
    """
    extensions = envelope.get("extensions")
    if not isinstance(extensions, dict):
        return
    halobridge = extensions.get("halobridge")
    if not isinstance(halobridge, dict):
        return
    for banned in list(halobridge.keys()):
        if isinstance(banned, str) and banned in EXTENSIONS_HALOBRIDGE_BANNED:
            halobridge.pop(banned, None)
    if not halobridge:
        extensions.pop("halobridge", None)


def _coerce_relationship_statuses(envelope: dict[str, Any]) -> None:
    """Coerce relationship.status values to the v3 enum; pin linker-discovered."""
    rels_block = envelope.get("relationships")
    if not isinstance(rels_block, dict):
        return
    rels = rels_block.get("relationships")
    if not isinstance(rels, list):
        return
    for entry in rels:
        if not isinstance(entry, dict):
            continue
        # Linker-discovered relationships must pin to suggested.
        discovered_by = entry.get("discovered_by") or ""
        if isinstance(discovered_by, str) and _DISCOVERED_BY_LINKER_RE.match(discovered_by):
            entry["status"] = "suggested"
            continue
        status = entry.get("status")
        if status not in _RELATIONSHIP_STATUS_ENUM:
            # Safe default for missing/invalid status.
            entry["status"] = "suggested"


def project_to_open_core(envelope: Any) -> dict[str, Any]:
    """Open-source v3 reference projector.

    Returns a v3-shaped envelope. Never raises. Coerces enums to safe
    defaults. Caps array cardinality at 512 per list. Strips the
    open-source-known forbidden keys + banned ``extensions.halobridge``
    keys.

    If the input declares ``schema_version == "gallodoc-core/v1"``, the
    projector calls ``migrate_v1_to_v3`` internally first, then projects.

    Does NOT strip platform-private patterns (``policy_formula``,
    ``halobridge_internal``, ``__internal__``) — those stay for the
    platform projector to handle. See the spec at
    ``docs/specs/gallodoc-core-v3-reference-projector.md``.
    """
    # Defensive: non-dict input collapses to an empty v3-shaped envelope.
    if not isinstance(envelope, dict):
        return {"schema_version": "gallodoc-core/v3"}

    # Deep-copy so we never mutate the caller's input.
    working: dict[str, Any] = copy.deepcopy(envelope)

    # If this is a v1 envelope, migrate first so we project a v3-shaped
    # result. Late import to avoid a circular dependency with migrator.py.
    declared = working.get("schema_version", "")
    if declared == "gallodoc-core/v1":
        from gallodoc.projection.migrator import migrate_v1_to_v3  # noqa: PLC0415

        working = migrate_v1_to_v3(working)

    # Recursive strip — drops forbidden key names + caps array sizes.
    stripped = _strip(working)
    if not isinstance(stripped, dict):
        return {"schema_version": "gallodoc-core/v3"}

    # Remove banned extensions.halobridge.<name> keys.
    _strip_banned_halobridge(stripped)

    # Coerce relationship status enums to safe defaults.
    _coerce_relationship_statuses(stripped)

    # Ensure schema_version is set to v3 if missing.
    if stripped.get("schema_version") != "gallodoc-core/v3":
        stripped["schema_version"] = "gallodoc-core/v3"

    return stripped


__all__ = ["project_to_open_core"]
