"""Open-core GalloDoc validator.

The default validator is stdlib-only and focuses on structural guarantees:

* required top-level sections are present,
* `schema_version` equals `gallodoc-core/v1`,
* required leaf fields inside each section have the right type,
* enums are honored.

If the optional ``jsonschema`` extra is installed (``pip install
gallodoc[schema]``), :func:`validate_with_jsonschema` performs the full
JSON-Schema check.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from gallodoc.projection.forbidden import EXTENSIONS_HALOBRIDGE_BANNED
from gallodoc.schema import load_schema


# Keys forbidden anywhere under ``execution_governance`` (case-insensitive).
_EXECUTION_GOVERNANCE_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
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
    }
)

_EXEC_GOV_SCHEMA_CONST = "gallodoc.execution_governance.v1.1"

_COMPLIANCE_V12_BLOCKS: dict[str, str] = {
    "consent_ledger": "gallodoc.consent_ledger.v1.2",
    "chain_of_custody": "gallodoc.chain_of_custody.v1.2",
    "human_decisions": "gallodoc.human_decisions.v1.2",
    "attestations": "gallodoc.attestations.v1.2",
    "redaction_manifest": "gallodoc.redaction_manifest.v1.2",
    "evidence_quality": "gallodoc.evidence_quality.v1.2",
}

_COMPLIANCE_V13_BLOCKS: dict[str, str] = {
    "data_residency": "gallodoc.data_residency.v1.3",
    "training_permissions": "gallodoc.training_permissions.v1.3",
    "model_risk": "gallodoc.model_risk.v1.3",
    "retention_status": "gallodoc.retention_status.v1.3",
}

_COMPLIANCE_V14_BLOCKS: dict[str, str] = {
    "agent_observability": "gallodoc.agent_observability.v1.4",
}

_COMPLIANCE_V15_BLOCKS: dict[str, str] = {
    "trust_decision": "gallodoc.trust_decision.v1.5",
}

_COMPLIANCE_V16_BLOCKS: dict[str, str] = {
    "agent_supply_chain_security": "gallodoc.agent_supply_chain_security.v1.6",
}

_COMPLIANCE_OPTIONAL_BLOCKS: dict[str, str] = {
    **_COMPLIANCE_V12_BLOCKS,
    **_COMPLIANCE_V13_BLOCKS,
    **_COMPLIANCE_V14_BLOCKS,
    **_COMPLIANCE_V15_BLOCKS,
    **_COMPLIANCE_V16_BLOCKS,
}

_COMPLIANCE_V12_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_signature",
        "signature_blob",
        "patient_name",
        "passport_number",
        "drivers_license",
        "street_address",
        "phone_number",
        "fax_number",
    }
)

_COMPLIANCE_V13_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "training_payload",
        "fine_tune_dataset",
        "training_batch",
        "model_weights",
        "lora_weights",
        "adapter_blob",
        "gradient_checkpoint",
    }
)

_COMPLIANCE_V14_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "chain_of_thought",
        "cot_trace",
        "hidden_reasoning",
        "thought_chain",
        "scratchpad",
        "retrieval_chunk_body",
        "phi_chunk",
        "tool_parameters",
        "raw_sql_text",
    }
)

_TRUST_DECISION_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_phi",
        "proprietary_weights",
        "formula_weights",
        "scoring_weight_matrix",
        "tenant_internals",
    }
)

_AGENT_SUPPLY_CHAIN_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_secret",
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
    }
)

_COMPLIANCE_V12_FORBIDDEN_KEYS: frozenset[str] = (
    _EXECUTION_GOVERNANCE_FORBIDDEN_KEYS
    | _COMPLIANCE_V12_EXTRA_FORBIDDEN_KEYS
    | _COMPLIANCE_V13_EXTRA_FORBIDDEN_KEYS
    | _COMPLIANCE_V14_EXTRA_FORBIDDEN_KEYS
    | _AGENT_SUPPLY_CHAIN_EXTRA_FORBIDDEN_KEYS
)

_TRUST_DECISION_FORBIDDEN_KEYS: frozenset[str] = (
    _COMPLIANCE_V12_FORBIDDEN_KEYS | _TRUST_DECISION_EXTRA_FORBIDDEN_KEYS
)


# ---------------------------------------------------------------------------
# GalloDoc Core v2.0 optional blocks
# ---------------------------------------------------------------------------

_COMPLIANCE_V20_BLOCKS: dict[str, str] = {
    "query_access": "gallodoc.query_access.v2.0",
    "vector_context": "gallodoc.vector_context.v2.0",
    "document_relationships": "gallodoc.document_relationships.v2.0",
    "temporal_versions": "gallodoc.temporal_versions.v2.0",
    "policy_governance": "gallodoc.policy_governance.v2.0",
    "access_control": "gallodoc.access_control.v2.0",
    "human_review": "gallodoc.human_review.v2.0",
    "workflow_execution": "gallodoc.workflow_execution.v2.0",
    "connector_lineage": "gallodoc.connector_lineage.v2.0",
    "compute_trace": "gallodoc.compute_trace.v2.0",
    "artifact_bom": "gallodoc.artifact_bom.v2.0",
}

# Forbidden raw / unsafe key names for every v2.0 block. These names MUST
# NOT appear anywhere inside a v2.0 block. Each set extends the v1.x base
# set so the same hygiene rules carry forward.
_V20_BASE_FORBIDDEN_KEYS: frozenset[str] = (
    _EXECUTION_GOVERNANCE_FORBIDDEN_KEYS
    | _COMPLIANCE_V12_EXTRA_FORBIDDEN_KEYS
    | _COMPLIANCE_V13_EXTRA_FORBIDDEN_KEYS
    | _COMPLIANCE_V14_EXTRA_FORBIDDEN_KEYS
    | _AGENT_SUPPLY_CHAIN_EXTRA_FORBIDDEN_KEYS
    | _TRUST_DECISION_EXTRA_FORBIDDEN_KEYS
    | frozenset(
        {
            "raw_secret",
            "plaintext_secret",
            "raw_code",
            "raw_phi",
            "ssn",
            "mrn",
            "dob",
            "tenant_id",
            "session_hash",
            "ip_hash",
            "password",
        }
    )
)

# Per-block additional forbidden keys.
_QUERY_ACCESS_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_sql",
        "sql_text",
        "sql_query",
        "raw_query",
        "raw_dialect_query",
    }
)

_VECTOR_CONTEXT_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_vector",
        "embedding_vector",
        "vector_payload",
        "raw_embedding",
        "chunk_text",
        "raw_chunk_text",
    }
)

_DOCUMENT_RELATIONSHIPS_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_field_value",
        "field_value",
        "patient_name",
        "raw_match_text",
    }
)

_TEMPORAL_VERSIONS_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_before",
        "raw_after",
        "before_value",
        "after_value",
        "raw_diff",
        "diff_text",
    }
)

_POLICY_GOVERNANCE_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_policy_body",
        "rego_source",
        "policy_source",
        "rule_body",
        "raw_rule_body",
    }
)

_ACCESS_CONTROL_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "user_id",
        "user_email",
        "user_name",
        "actor_id",
        "actor_email",
        "actor_name",
    }
)

_HUMAN_REVIEW_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_notes",
        "reviewer_id",
        "reviewer_email",
        "reviewer_name",
        "notes_body",
        "reviewer_user_id",
    }
)

_WORKFLOW_EXECUTION_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_input",
        "raw_output",
        "input_payload",
        "output_payload",
        "stack_trace",
        "raw_stack_trace",
    }
)

_CONNECTOR_LINEAGE_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_url",
        "raw_endpoint",
        "raw_record",
        "record_payload",
        "credential",
        "auth_credential",
    }
)

_COMPUTE_TRACE_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "raw_log",
        "log_body",
        "raw_message",
        "raw_metric_values",
    }
)

_ARTIFACT_BOM_EXTRA_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "advisory_body",
        "raw_advisory",
        "exploit_payload",
        "malware_payload",
    }
)

_V20_FORBIDDEN_KEYS_BY_BLOCK: dict[str, frozenset[str]] = {
    "query_access": _V20_BASE_FORBIDDEN_KEYS | _QUERY_ACCESS_EXTRA_FORBIDDEN_KEYS,
    "vector_context": _V20_BASE_FORBIDDEN_KEYS | _VECTOR_CONTEXT_EXTRA_FORBIDDEN_KEYS,
    "document_relationships": _V20_BASE_FORBIDDEN_KEYS | _DOCUMENT_RELATIONSHIPS_EXTRA_FORBIDDEN_KEYS,
    "temporal_versions": _V20_BASE_FORBIDDEN_KEYS | _TEMPORAL_VERSIONS_EXTRA_FORBIDDEN_KEYS,
    "policy_governance": _V20_BASE_FORBIDDEN_KEYS | _POLICY_GOVERNANCE_EXTRA_FORBIDDEN_KEYS,
    "access_control": _V20_BASE_FORBIDDEN_KEYS | _ACCESS_CONTROL_EXTRA_FORBIDDEN_KEYS,
    "human_review": _V20_BASE_FORBIDDEN_KEYS | _HUMAN_REVIEW_EXTRA_FORBIDDEN_KEYS,
    "workflow_execution": _V20_BASE_FORBIDDEN_KEYS | _WORKFLOW_EXECUTION_EXTRA_FORBIDDEN_KEYS,
    "connector_lineage": _V20_BASE_FORBIDDEN_KEYS | _CONNECTOR_LINEAGE_EXTRA_FORBIDDEN_KEYS,
    "compute_trace": _V20_BASE_FORBIDDEN_KEYS | _COMPUTE_TRACE_EXTRA_FORBIDDEN_KEYS,
    "artifact_bom": _V20_BASE_FORBIDDEN_KEYS | _ARTIFACT_BOM_EXTRA_FORBIDDEN_KEYS,
}

# ---------------------------------------------------------------------------
# v3 validator rules — additive over the v1.x / v2.0 structural + safety rules.
# See docs/specs/gallodoc-core-v3-master-spec.md §7.
# ---------------------------------------------------------------------------

# v3 rule 2 — banned `extensions.halobridge.<known_block>` keys. 13 v1.2–v1.6
# compliance block names plus `federation` (Decision 4 — federation must be
# top-level, not buried under extensions). 14 names total. The canonical set
# lives in ``gallodoc.projection.forbidden`` and is imported above.

# v3 rule 1 — linker entries pin to `suggested`. Regex anchors to "linker"
# anywhere in `discovered_by`, case-insensitive. Per Decision 3 in
# docs/v3-design/07_decisions.md, the linker cannot accidentally publish a
# confirmed relationship.
_DISCOVERED_BY_LINKER_RE = re.compile(r".*linker.*", re.IGNORECASE)


_JWTISH = re.compile(r"^eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.")
_URL_IN_STRING = re.compile(r"(?i)https?://")
_EMAIL_DISALLOWED = re.compile(
    r"\b[\w.+-]+@(?!example\.com\b|halobridge\.ai\b)[\w.-]+\.[a-z]{2,}\b",
    re.IGNORECASE,
)
_SSN_LIKE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """A single validation problem."""

    path: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ValidationResult:
    """Outcome of validating a single envelope."""

    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    schema_version: str = ""
    used_jsonschema: bool = False

    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "schema_version": self.schema_version,
            "used_jsonschema": self.used_jsonschema,
            "errors": [i.__dict__ for i in self.issues if i.severity == "error"],
            "warnings": [i.__dict__ for i in self.issues if i.severity == "warning"],
        }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_envelope(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Stdlib-only validation
# ---------------------------------------------------------------------------


_PYTHON_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "object": (dict,),
    "array": (list,),
}


def _check_type(value: Any, json_type: Any) -> bool:
    """Lenient JSON-Schema type check that handles ``["string", "null"]``."""
    if json_type is None:
        return True
    if isinstance(json_type, list):
        types = [t for t in json_type if t != "null"]
        if value is None:
            return "null" in json_type
        return any(_check_type(value, t) for t in types)
    py_types = _PYTHON_TYPE_MAP.get(json_type)
    if py_types is None:
        return True
    if json_type == "integer" and isinstance(value, bool):
        return False  # bool is an int in Python — reject for integer.
    return isinstance(value, py_types)


def _check_enum(value: Any, allowed: Iterable[Any]) -> bool:
    return value in list(allowed)


def _execution_governance_forbidden_key(key: str) -> bool:
    if not isinstance(key, str):
        return False
    return key.strip().lower() in _EXECUTION_GOVERNANCE_FORBIDDEN_KEYS


def _scan_execution_governance_leaks(value: Any, base_path: str, issues: list[ValidationIssue], *, depth: int = 0) -> None:
    """Reject forbidden keys and JWT-shaped strings under ``execution_governance``."""
    if depth > 24:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{base_path}.{k}".lstrip(".")
            if _execution_governance_forbidden_key(k):
                issues.append(
                    ValidationIssue(
                        path=path,
                        message=f"forbidden key under execution_governance: {k!r}",
                    )
                )
                continue
            _scan_execution_governance_leaks(v, path, issues, depth=depth + 1)
    elif isinstance(value, list):
        for i, item in enumerate(value[:512]):
            _scan_execution_governance_leaks(item, f"{base_path}[{i}]", issues, depth=depth + 1)
    elif isinstance(value, str) and _JWTISH.match(value.strip()):
        issues.append(
            ValidationIssue(
                path=base_path,
                message="JWT-shaped string forbidden under execution_governance",
            )
        )


def _compliance_v12_forbidden_key(key: str) -> bool:
    if not isinstance(key, str):
        return False
    return key.strip().lower() in _COMPLIANCE_V12_FORBIDDEN_KEYS


def _trust_decision_forbidden_key(key: str) -> bool:
    if not isinstance(key, str):
        return False
    return key.strip().lower() in _TRUST_DECISION_FORBIDDEN_KEYS


def _scan_compliance_v12_leaks(
    value: Any,
    base_path: str,
    issues: list[ValidationIssue],
    *,
    depth: int = 0,
) -> None:
    """Forbidden keys, JWT-shaped strings, URLs, disallowed emails, SSN-shaped strings."""
    if depth > 28:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{base_path}.{k}".lstrip(".")
            if _compliance_v12_forbidden_key(k):
                issues.append(
                    ValidationIssue(
                        path=path,
                        message=f"forbidden key under compliance extension block: {k!r}",
                    )
                )
                continue
            _scan_compliance_v12_leaks(v, path, issues, depth=depth + 1)
    elif isinstance(value, list):
        for i, item in enumerate(value[:512]):
            _scan_compliance_v12_leaks(item, f"{base_path}[{i}]", issues, depth=depth + 1)
    elif isinstance(value, str):
        s = value.strip()
        if _JWTISH.match(s):
            issues.append(
                ValidationIssue(path=base_path, message="JWT-shaped string forbidden under compliance extension blocks")
            )
        if _URL_IN_STRING.search(s):
            issues.append(
                ValidationIssue(path=base_path, message="URL-like string forbidden under compliance extension blocks")
            )
        if _EMAIL_DISALLOWED.search(s):
            issues.append(
                ValidationIssue(path=base_path, message="non-allowlisted email domain forbidden under compliance extension blocks")
            )
        if _SSN_LIKE.search(s):
            issues.append(
                ValidationIssue(path=base_path, message="SSN-shaped literal forbidden under compliance extension blocks")
            )


def _scan_trust_decision_leaks(
    value: Any,
    base_path: str,
    issues: list[ValidationIssue],
    *,
    depth: int = 0,
) -> None:
    """Forbidden keys and JWT/URL/email/SSN-shaped strings under ``trust_decision``."""
    if depth > 28:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{base_path}.{k}".lstrip(".")
            if _trust_decision_forbidden_key(k):
                issues.append(
                    ValidationIssue(
                        path=path,
                        message=f"forbidden key under trust_decision: {k!r}",
                    )
                )
                continue
            _scan_trust_decision_leaks(v, path, issues, depth=depth + 1)
    elif isinstance(value, list):
        for i, item in enumerate(value[:512]):
            _scan_trust_decision_leaks(item, f"{base_path}[{i}]", issues, depth=depth + 1)
    elif isinstance(value, str):
        s = value.strip()
        if _JWTISH.match(s):
            issues.append(
                ValidationIssue(path=base_path, message="JWT-shaped string forbidden under trust_decision")
            )
        if _URL_IN_STRING.search(s):
            issues.append(ValidationIssue(path=base_path, message="URL-like string forbidden under trust_decision"))
        if _EMAIL_DISALLOWED.search(s):
            issues.append(
                ValidationIssue(path=base_path, message="non-allowlisted email domain forbidden under trust_decision")
            )
        if _SSN_LIKE.search(s):
            issues.append(ValidationIssue(path=base_path, message="SSN-shaped literal forbidden under trust_decision"))


def _apply_trust_decision_public_safety_rules(envelope: dict[str, Any], issues: list[ValidationIssue]) -> None:
    block = envelope.get("trust_decision")
    if block is None:
        return
    if not isinstance(block, dict):
        issues.append(ValidationIssue(path="trust_decision", message="expected object"))
        return
    declared = block.get("schema_version", "")
    const = _COMPLIANCE_V15_BLOCKS["trust_decision"]
    if declared != const:
        issues.append(
            ValidationIssue(
                path="trust_decision.schema_version",
                message=f"expected {const!r}, got {declared!r}",
            )
        )
    _scan_trust_decision_leaks(block, "trust_decision", issues)


def _apply_compliance_v12_public_safety_rules(envelope: dict[str, Any], issues: list[ValidationIssue]) -> None:
    for key, const in _COMPLIANCE_OPTIONAL_BLOCKS.items():
        if key == "trust_decision":
            continue
        block = envelope.get(key)
        if block is None:
            continue
        if not isinstance(block, dict):
            issues.append(ValidationIssue(path=key, message="expected object"))
            continue
        declared = block.get("schema_version", "")
        if declared != const:
            issues.append(
                ValidationIssue(
                    path=f"{key}.schema_version",
                    message=f"expected {const!r}, got {declared!r}",
                )
            )
        _scan_compliance_v12_leaks(block, key, issues)


def _apply_execution_governance_public_safety_rules(envelope: dict[str, Any], issues: list[ValidationIssue]) -> None:
    block = envelope.get("execution_governance")
    if block is None:
        return
    if not isinstance(block, dict):
        issues.append(ValidationIssue(path="execution_governance", message="expected object"))
        return
    declared = block.get("schema_version", "")
    if declared != _EXEC_GOV_SCHEMA_CONST:
        issues.append(
            ValidationIssue(
                path="execution_governance.schema_version",
                message=f"expected {_EXEC_GOV_SCHEMA_CONST!r}, got {declared!r}",
            )
        )
    _scan_execution_governance_leaks(block, "execution_governance", issues)


def _scan_v20_block_leaks(
    value: Any,
    base_path: str,
    issues: list[ValidationIssue],
    forbidden: frozenset[str],
    *,
    depth: int = 0,
) -> None:
    """Reject forbidden keys, JWTs, URLs, disallowed emails, and SSN-shaped strings under a v2.0 block."""
    if depth > 28:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{base_path}.{k}".lstrip(".")
            if isinstance(k, str) and k.strip().lower() in forbidden:
                issues.append(
                    ValidationIssue(
                        path=path,
                        message=f"forbidden key under v2.0 block: {k!r}",
                    )
                )
                continue
            _scan_v20_block_leaks(v, path, issues, forbidden, depth=depth + 1)
    elif isinstance(value, list):
        for i, item in enumerate(value[:512]):
            _scan_v20_block_leaks(item, f"{base_path}[{i}]", issues, forbidden, depth=depth + 1)
    elif isinstance(value, str):
        s = value.strip()
        if _JWTISH.match(s):
            issues.append(ValidationIssue(path=base_path, message="JWT-shaped string forbidden under v2.0 block"))
        if _EMAIL_DISALLOWED.search(s):
            issues.append(
                ValidationIssue(path=base_path, message="non-allowlisted email domain forbidden under v2.0 block")
            )
        if _SSN_LIKE.search(s):
            issues.append(ValidationIssue(path=base_path, message="SSN-shaped literal forbidden under v2.0 block"))


def _validate_v20_field_ranges(
    block_key: str,
    block: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    """Light shape checks for v2.0 blocks: 0-100 score / 0-1 confidence ranges, ISO timestamps, required IDs."""
    iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:\d{2})$")

    def _check_iso(path: str, value: Any) -> None:
        if isinstance(value, str) and value and not iso_re.match(value):
            issues.append(ValidationIssue(path=path, message=f"expected ISO-8601 timestamp, got {value!r}"))

    def _check_range(path: str, value: Any, lo: float, hi: float) -> None:
        if isinstance(value, (int, float)) and not (lo <= value <= hi):
            issues.append(
                ValidationIssue(path=path, message=f"value {value!r} not in [{lo}, {hi}]")
            )

    def _check_required(parent_path: str, item: dict[str, Any], field: str) -> None:
        if field not in item or item[field] in (None, ""):
            issues.append(
                ValidationIssue(path=f"{parent_path}.{field}", message="required field missing")
            )

    # Per-block lightweight shape rules.
    if block_key == "query_access":
        for i, q in enumerate(block.get("saved_queries") or []):
            base = f"query_access.saved_queries[{i}]"
            if isinstance(q, dict):
                for f in ("query_id", "name", "query_type", "created_by_role", "created_at"):
                    _check_required(base, q, f)
                _check_iso(f"{base}.created_at", q.get("created_at"))
                if "max_results" in q and isinstance(q["max_results"], int) and q["max_results"] < 0:
                    issues.append(ValidationIssue(path=f"{base}.max_results", message="max_results must be >= 0"))
        for i, r in enumerate(block.get("query_receipts") or []):
            base = f"query_access.query_receipts[{i}]"
            if isinstance(r, dict):
                for f in ("receipt_id", "query_id", "executed_by_role", "executed_at"):
                    _check_required(base, r, f)
                _check_iso(f"{base}.executed_at", r.get("executed_at"))
    elif block_key == "vector_context":
        for i, idx in enumerate(block.get("embedding_indexes") or []):
            base = f"vector_context.embedding_indexes[{i}]"
            if isinstance(idx, dict):
                for f in ("index_id", "embedding_model_hash_or_id", "dimensions", "created_at"):
                    _check_required(base, idx, f)
                _check_iso(f"{base}.created_at", idx.get("created_at"))
        for i, c in enumerate(block.get("embedding_chunks") or []):
            base = f"vector_context.embedding_chunks[{i}]"
            if isinstance(c, dict):
                for f in ("chunk_id", "text_hash", "embedding_hash", "created_at"):
                    _check_required(base, c, f)
                _check_iso(f"{base}.created_at", c.get("created_at"))
    elif block_key == "document_relationships":
        allowed_types = {
            "duplicate_of", "version_of", "supersedes", "belongs_to", "supports",
            "contradicts", "same_claim", "same_patient", "same_customer",
            "same_contract", "same_invoice", "derived_from", "related_to",
        }
        allowed_status = {"suggested", "confirmed", "rejected"}
        for i, rel in enumerate(block.get("relationships") or []):
            base = f"document_relationships.relationships[{i}]"
            if isinstance(rel, dict):
                for f in ("relationship_id", "source_document_ref", "target_document_ref", "relationship_type", "status", "created_at"):
                    _check_required(base, rel, f)
                _check_iso(f"{base}.created_at", rel.get("created_at"))
                if rel.get("relationship_type") and rel["relationship_type"] not in allowed_types:
                    issues.append(
                        ValidationIssue(path=f"{base}.relationship_type", message=f"value {rel['relationship_type']!r} not in enum")
                    )
                if rel.get("status") and rel["status"] not in allowed_status:
                    issues.append(
                        ValidationIssue(path=f"{base}.status", message=f"value {rel['status']!r} not in enum")
                    )
                _check_range(f"{base}.confidence", rel.get("confidence"), 0.0, 1.0)
    elif block_key == "temporal_versions":
        allowed_status = {"draft", "active", "superseded", "archived"}
        allowed_changes = {
            "artifact_added", "artifact_updated", "decision_changed", "policy_changed",
            "redaction_changed", "relationship_changed", "trust_score_changed",
        }
        for i, v in enumerate(block.get("versions") or []):
            base = f"temporal_versions.versions[{i}]"
            if isinstance(v, dict):
                for f in ("version_id", "document_hash", "gallodoc_hash", "created_at", "status"):
                    _check_required(base, v, f)
                _check_iso(f"{base}.created_at", v.get("created_at"))
                if v.get("status") and v["status"] not in allowed_status:
                    issues.append(ValidationIssue(path=f"{base}.status", message=f"value {v['status']!r} not in enum"))
        for i, c in enumerate(block.get("change_events") or []):
            base = f"temporal_versions.change_events[{i}]"
            if isinstance(c, dict) and c.get("change_type") and c["change_type"] not in allowed_changes:
                issues.append(ValidationIssue(path=f"{base}.change_type", message=f"value {c['change_type']!r} not in enum"))
    elif block_key == "policy_governance":
        allowed_lang = {"json_rules", "rego", "cel", "custom"}
        allowed_action = {"allow", "warn", "block", "require_review"}
        for i, ps in enumerate(block.get("policy_sets") or []):
            base = f"policy_governance.policy_sets[{i}]"
            if isinstance(ps, dict):
                for f in ("policy_set_id", "name", "version", "language", "policy_hash", "status"):
                    _check_required(base, ps, f)
                if ps.get("language") and ps["language"] not in allowed_lang:
                    issues.append(ValidationIssue(path=f"{base}.language", message=f"value {ps['language']!r} not in enum"))
        for i, r in enumerate(block.get("policy_rules") or []):
            base = f"policy_governance.policy_rules[{i}]"
            if isinstance(r, dict) and r.get("action") and r["action"] not in allowed_action:
                issues.append(ValidationIssue(path=f"{base}.action", message=f"value {r['action']!r} not in enum"))
    elif block_key == "access_control":
        allowed_decision = {"allow", "deny", "masked"}
        allowed_display = {"hidden", "masked", "hashed", "role_based"}
        for i, r in enumerate(block.get("access_receipts") or []):
            base = f"access_control.access_receipts[{i}]"
            if isinstance(r, dict):
                for f in ("receipt_id", "actor_role", "action", "subject_ref", "decision", "accessed_at"):
                    _check_required(base, r, f)
                _check_iso(f"{base}.accessed_at", r.get("accessed_at"))
                if r.get("decision") and r["decision"] not in allowed_decision:
                    issues.append(ValidationIssue(path=f"{base}.decision", message=f"value {r['decision']!r} not in enum"))
        for i, m in enumerate(block.get("masking_rules") or []):
            base = f"access_control.masking_rules[{i}]"
            if isinstance(m, dict) and m.get("display_mode") and m["display_mode"] not in allowed_display:
                issues.append(ValidationIssue(path=f"{base}.display_mode", message=f"value {m['display_mode']!r} not in enum"))
    elif block_key == "human_review":
        allowed_action = {"approve", "reject", "correct", "escalate", "request_more_evidence"}
        for i, a in enumerate(block.get("review_actions") or []):
            base = f"human_review.review_actions[{i}]"
            if isinstance(a, dict):
                for f in ("review_id", "subject_ref", "reviewer_role", "action", "decided_at"):
                    _check_required(base, a, f)
                _check_iso(f"{base}.decided_at", a.get("decided_at"))
                if a.get("action") and a["action"] not in allowed_action:
                    issues.append(ValidationIssue(path=f"{base}.action", message=f"value {a['action']!r} not in enum"))
    elif block_key == "workflow_execution":
        allowed_status = {"queued", "running", "completed", "failed", "blocked", "skipped"}
        allowed_step_types = {"ingest", "ocr", "classify", "extract", "review", "verify", "export", "scan", "notify"}
        for i, r in enumerate(block.get("workflow_runs") or []):
            base = f"workflow_execution.workflow_runs[{i}]"
            if isinstance(r, dict):
                for f in ("workflow_run_id", "workflow_name", "status", "started_at"):
                    _check_required(base, r, f)
                _check_iso(f"{base}.started_at", r.get("started_at"))
                if r.get("completed_at"):
                    _check_iso(f"{base}.completed_at", r.get("completed_at"))
                if r.get("status") and r["status"] not in allowed_status:
                    issues.append(ValidationIssue(path=f"{base}.status", message=f"value {r['status']!r} not in enum"))
        for i, s in enumerate(block.get("workflow_steps") or []):
            base = f"workflow_execution.workflow_steps[{i}]"
            if isinstance(s, dict) and s.get("step_type") and s["step_type"] not in allowed_step_types:
                issues.append(ValidationIssue(path=f"{base}.step_type", message=f"value {s['step_type']!r} not in enum"))
    elif block_key == "connector_lineage":
        for i, sr in enumerate(block.get("sync_runs") or []):
            base = f"connector_lineage.sync_runs[{i}]"
            if isinstance(sr, dict):
                for f in ("sync_run_id", "connector_slug", "started_at", "status"):
                    _check_required(base, sr, f)
                _check_iso(f"{base}.started_at", sr.get("started_at"))
                if sr.get("completed_at"):
                    _check_iso(f"{base}.completed_at", sr.get("completed_at"))
    elif block_key == "compute_trace":
        allowed_span_types = {"llm_call", "tool_call", "retrieval", "policy_eval", "scanner", "sandbox", "export", "api_call"}
        for i, sp in enumerate(block.get("spans") or []):
            base = f"compute_trace.spans[{i}]"
            if isinstance(sp, dict):
                for f in ("span_id", "trace_id", "span_name", "span_type", "started_at", "status"):
                    _check_required(base, sp, f)
                _check_iso(f"{base}.started_at", sp.get("started_at"))
                if sp.get("ended_at"):
                    _check_iso(f"{base}.ended_at", sp.get("ended_at"))
                if sp.get("span_type") and sp["span_type"] not in allowed_span_types:
                    issues.append(ValidationIssue(path=f"{base}.span_type", message=f"value {sp['span_type']!r} not in enum"))
    elif block_key == "artifact_bom":
        allowed_types = {"document", "model", "skill", "mcp_tool", "python_package", "npm_package", "container", "dataset"}
        for i, c in enumerate(block.get("components") or []):
            base = f"artifact_bom.components[{i}]"
            if isinstance(c, dict):
                for f in ("component_id", "name", "version", "component_type", "hash", "bom_ref"):
                    _check_required(base, c, f)
                if c.get("component_type") and c["component_type"] not in allowed_types:
                    issues.append(ValidationIssue(path=f"{base}.component_type", message=f"value {c['component_type']!r} not in enum"))


def _apply_v20_public_safety_rules(envelope: dict[str, Any], issues: list[ValidationIssue]) -> None:
    for key, const in _COMPLIANCE_V20_BLOCKS.items():
        block = envelope.get(key)
        if block is None:
            continue
        if not isinstance(block, dict):
            issues.append(ValidationIssue(path=key, message="expected object"))
            continue
        declared = block.get("schema_version", "")
        if declared != const:
            issues.append(
                ValidationIssue(
                    path=f"{key}.schema_version",
                    message=f"expected {const!r}, got {declared!r}",
                )
            )
        forbidden = _V20_FORBIDDEN_KEYS_BY_BLOCK[key]
        _scan_v20_block_leaks(block, key, issues, forbidden)
        _validate_v20_field_ranges(key, block, issues)


def _validate_object(
    value: Any,
    schema_node: dict[str, Any],
    *,
    path: str,
    issues: list[ValidationIssue],
    depth: int = 0,
) -> None:
    if depth > 12:
        return
    if not isinstance(value, dict):
        if "object" in (schema_node.get("type") or ""):
            issues.append(ValidationIssue(path=path, message=f"expected object, got {type(value).__name__}"))
        return

    required = schema_node.get("required") or []
    for r in required:
        if r not in value:
            issues.append(ValidationIssue(path=f"{path}.{r}".lstrip("."), message="required field missing"))

    properties = schema_node.get("properties") or {}
    for k, sub in properties.items():
        if k not in value:
            continue
        sub_path = f"{path}.{k}".lstrip(".")
        sub_value = value[k]
        sub_type = sub.get("type")
        if sub_type and not _check_type(sub_value, sub_type):
            issues.append(ValidationIssue(path=sub_path, message=f"expected type {sub_type}, got {type(sub_value).__name__}"))
            continue
        if "const" in sub and sub_value != sub["const"]:
            issues.append(ValidationIssue(path=sub_path, message=f"expected const {sub['const']!r}, got {sub_value!r}"))
        if "enum" in sub and not _check_enum(sub_value, sub["enum"]):
            issues.append(ValidationIssue(path=sub_path, message=f"value {sub_value!r} not in enum {sub['enum']}"))
        if isinstance(sub_value, dict) and (sub.get("properties") or sub.get("required")):
            _validate_object(sub_value, sub, path=sub_path, issues=issues, depth=depth + 1)
        if isinstance(sub_value, list) and isinstance(sub.get("items"), dict):
            item_schema = sub["items"]
            for i, item in enumerate(sub_value[:256]):
                item_path = f"{sub_path}[{i}]"
                item_type = item_schema.get("type")
                if item_type and not _check_type(item, item_type):
                    issues.append(ValidationIssue(path=item_path, message=f"expected item type {item_type}, got {type(item).__name__}"))
                    continue
                if isinstance(item, dict):
                    _validate_object(item, item_schema, path=item_path, issues=issues, depth=depth + 1)


def _validate_v1(envelope: dict[str, Any]) -> ValidationResult:
    """Stdlib-only validation against the v1 (frozen) schema.

    Returns a :class:`ValidationResult`. Errors prevent the envelope from
    being considered valid; warnings are surfaced but do not fail the check.

    This function preserves the original ``validate_envelope`` behavior
    unchanged — it is the parallel-validation guarantee for v1 envelopes
    during the 6-month deprecation window beginning 2026-05-16.
    """
    schema = load_schema(version="gallodoc-core/v1")
    issues: list[ValidationIssue] = []

    if not isinstance(envelope, dict):
        return ValidationResult(
            valid=False,
            issues=[ValidationIssue(path="$", message=f"envelope must be a JSON object, got {type(envelope).__name__}")],
        )

    declared_version = envelope.get("schema_version", "")
    if declared_version != "gallodoc-core/v1":
        issues.append(
            ValidationIssue(
                path="schema_version",
                message=f"expected 'gallodoc-core/v1', got {declared_version!r}",
            )
        )

    _validate_object(envelope, schema, path="", issues=issues)
    _apply_execution_governance_public_safety_rules(envelope, issues)
    _apply_compliance_v12_public_safety_rules(envelope, issues)
    _apply_trust_decision_public_safety_rules(envelope, issues)
    _apply_v20_public_safety_rules(envelope, issues)

    return ValidationResult(
        valid=not any(i.severity == "error" for i in issues),
        issues=issues,
        schema_version=declared_version or "",
        used_jsonschema=False,
    )


def _apply_v3_validator_rules(envelope: dict[str, Any], issues: list[ValidationIssue]) -> None:
    """Apply the v3-specific additive validator rules.

    1. Linker-discovered relationships pin to ``status == "suggested"``
       unless a matching ``relationship_decisions[]`` record exists.
    2. ``extensions.halobridge.<known_block>`` is forbidden for the 13
       v1.2–v1.6 compliance block names + ``federation``.
    3. Nested ``trust.score`` or ``trust.decision`` objects are forbidden —
       v3's trust block is flat (Decision 2).
    4. ``federation.cross_tenant_policy.sharing_scope`` must be in the
       5-value enum (Codex 08).
    5. ``federation.matching_receipts[].raw_data_exposed`` must be
       ``false`` in v3.0 (Codex 08).

    See docs/specs/gallodoc-core-v3-master-spec.md §7 and
    docs/specs/gallodoc-core-v3-federation.md §7.
    """
    # Rule 1: linker-discovered relationships gate on the decision-record audit
    # trail (Decision 3). `discovered_by` is preserved through the lifecycle,
    # so the rule no longer pins status to "suggested" unconditionally — it
    # requires a matching record in `relationships.relationship_decisions[]`
    # whenever status is `confirmed` or `rejected`.
    #
    # Valid combinations for a linker-discovered relationship:
    #   status = "suggested" + no matching decision record   → valid
    #   status = "confirmed" + matching decision record       → valid
    #   status = "rejected"  + matching decision record       → valid
    #
    # Invalid:
    #   status = "confirmed"|"rejected" + no decision record  → reject
    #   status = "suggested" + decision record exists         → reject (inconsistent)
    #   status = anything else                                → reject
    rel_block = envelope.get("relationships")
    if isinstance(rel_block, dict):
        rels = rel_block.get("relationships") or []
        decisions = rel_block.get("relationship_decisions") or []
        decided_rel_ids: set[str] = set()
        if isinstance(decisions, list):
            for d in decisions:
                if isinstance(d, dict):
                    rid = d.get("relationship_id")
                    if isinstance(rid, str):
                        decided_rel_ids.add(rid)
        if isinstance(rels, list):
            for i, r in enumerate(rels):
                if not isinstance(r, dict):
                    continue
                discovered_by = r.get("discovered_by", "")
                if not isinstance(discovered_by, str):
                    continue
                if not _DISCOVERED_BY_LINKER_RE.match(discovered_by):
                    continue
                status = r.get("status")
                rel_id = r.get("relationship_id") if isinstance(r.get("relationship_id"), str) else None
                has_decision = rel_id is not None and rel_id in decided_rel_ids
                if status == "suggested":
                    if has_decision:
                        issues.append(
                            ValidationIssue(
                                path=f"relationships.relationships[{i}].status",
                                message=(
                                    f"linker-discovered relationship (discovered_by={discovered_by!r}, "
                                    f"relationship_id={rel_id!r}) has status='suggested' but a matching "
                                    f"entry exists in relationships.relationship_decisions[] — "
                                    f"inconsistent state (Decision 3)"
                                ),
                            )
                        )
                elif status in ("confirmed", "rejected"):
                    if not has_decision:
                        issues.append(
                            ValidationIssue(
                                path=f"relationships.relationships[{i}].status",
                                message=(
                                    f"linker-discovered relationship (discovered_by={discovered_by!r}, "
                                    f"relationship_id={rel_id!r}) has status={status!r} but no matching "
                                    f"entry in relationships.relationship_decisions[] — record the "
                                    f"decision via apply_relationship_decision() (Decision 3)"
                                ),
                            )
                        )
                else:
                    issues.append(
                        ValidationIssue(
                            path=f"relationships.relationships[{i}].status",
                            message=(
                                f"linker-discovered relationship (discovered_by={discovered_by!r}) "
                                f"must have status in {{'suggested', 'confirmed', 'rejected'}}, got {status!r}"
                            ),
                        )
                    )

    # Rule 2: banned extensions.halobridge.<known_block> keys.
    extensions = envelope.get("extensions")
    if isinstance(extensions, dict):
        halobridge = extensions.get("halobridge")
        if isinstance(halobridge, dict):
            for key in halobridge.keys():
                if not isinstance(key, str):
                    continue
                if key in EXTENSIONS_HALOBRIDGE_BANNED:
                    issues.append(
                        ValidationIssue(
                            path=f"extensions.halobridge.{key}",
                            message=(
                                f"forbidden key {key!r} under extensions.halobridge — "
                                f"v1.2–v1.6 compliance blocks + federation must live at top level only in v3"
                            ),
                        )
                    )

    # Rule 3: trust block is flat — no nested trust.score or trust.decision objects.
    trust = envelope.get("trust")
    if isinstance(trust, dict):
        if isinstance(trust.get("score"), dict):
            issues.append(
                ValidationIssue(
                    path="trust.score",
                    message=(
                        "nested `trust.score` object is forbidden in v3 — the trust block is flat "
                        "(see Decision 2 in docs/v3-design/07_decisions.md)"
                    ),
                )
            )
        if isinstance(trust.get("decision"), dict):
            issues.append(
                ValidationIssue(
                    path="trust.decision",
                    message=(
                        "nested `trust.decision` object is forbidden in v3 — the trust block is flat "
                        "(see Decision 2 in docs/v3-design/07_decisions.md)"
                    ),
                )
            )

    # Rule 4 (Codex 08): federation.cross_tenant_policy.sharing_scope must be
    # in the 5-value enum. The structural enum check from the schema (Codex 08
    # commit 2) covers this when jsonschema is installed; this rule emits a
    # cleaner stdlib-only error message and runs unconditionally.
    fed = envelope.get("federation")
    if isinstance(fed, dict):
        policy = fed.get("cross_tenant_policy")
        if isinstance(policy, dict):
            scope = policy.get("sharing_scope")
            allowed_scopes = {
                "tenant_private",
                "fingerprint_only",
                "semantic_only",
                "trusted_exchange",
                "disabled",
            }
            if scope is not None and scope not in allowed_scopes:
                issues.append(
                    ValidationIssue(
                        path="federation.cross_tenant_policy.sharing_scope",
                        message=(
                            f"sharing_scope must be one of {sorted(allowed_scopes)}, "
                            f"got {scope!r} (Decision 4)"
                        ),
                    )
                )

    # Rule 5 (Codex 08): federation.matching_receipts[].raw_data_exposed
    # must be false in v3.0. Federation receipts may carry hashes and refs
    # only, never raw values. Reserved for v4 under more rigorous controls.
    if isinstance(fed, dict):
        receipts = fed.get("matching_receipts") or []
        if isinstance(receipts, list):
            for i, r in enumerate(receipts):
                if not isinstance(r, dict):
                    continue
                if r.get("raw_data_exposed") is True:
                    issues.append(
                        ValidationIssue(
                            path=f"federation.matching_receipts[{i}].raw_data_exposed",
                            message=(
                                "raw_data_exposed must be false in v3.0 — federation "
                                "receipts may carry hashes and refs only, never raw values "
                                "(Decision 4)"
                            ),
                        )
                    )


def _validate_v3(envelope: dict[str, Any]) -> ValidationResult:
    """Stdlib-only validation against the v3 schema.

    Runs the same structural check the v1 validator does, against the v3
    schema, and carries forward every v1.x / v2.0 public-safety rule
    (``execution_governance``, v1.2 compliance, ``trust_decision`` carry-overs,
    v2.0 forbidden-key scans). The three additive v3 validator rules
    (linker-pinned-to-suggested, banned ``extensions.halobridge.<known_block>``
    keys, flat trust block) ship in commit 4.
    """
    schema = load_schema(version="gallodoc-core/v3")
    issues: list[ValidationIssue] = []

    if not isinstance(envelope, dict):
        return ValidationResult(
            valid=False,
            issues=[ValidationIssue(path="$", message=f"envelope must be a JSON object, got {type(envelope).__name__}")],
        )

    declared_version = envelope.get("schema_version", "")
    if declared_version != "gallodoc-core/v3":
        issues.append(
            ValidationIssue(
                path="schema_version",
                message=f"expected 'gallodoc-core/v3', got {declared_version!r}",
            )
        )

    _validate_object(envelope, schema, path="", issues=issues)
    # Carry-forward public-safety rules — v3 is additive, so every v1.x / v2.0
    # safety rule still applies to v3 envelopes that include those blocks.
    _apply_execution_governance_public_safety_rules(envelope, issues)
    _apply_compliance_v12_public_safety_rules(envelope, issues)
    _apply_trust_decision_public_safety_rules(envelope, issues)
    _apply_v20_public_safety_rules(envelope, issues)
    # v3-specific additive rules.
    _apply_v3_validator_rules(envelope, issues)

    return ValidationResult(
        valid=not any(i.severity == "error" for i in issues),
        issues=issues,
        schema_version=declared_version or "",
        used_jsonschema=False,
    )


def validate_envelope(envelope: dict[str, Any]) -> ValidationResult:
    """Top-level validator. Dispatches by ``envelope["schema_version"]``.

    - ``"gallodoc-core/v1"`` → :func:`_validate_v1` (parallel-supported).
    - ``"gallodoc-core/v3"`` → :func:`_validate_v3` (active).
    - anything else (including missing) → ``valid=False`` with an
      ``"unknown schema version"`` issue.
    """
    if not isinstance(envelope, dict):
        return ValidationResult(
            valid=False,
            issues=[ValidationIssue(path="$", message=f"envelope must be a JSON object, got {type(envelope).__name__}")],
        )
    declared = envelope.get("schema_version", "")
    if declared == "gallodoc-core/v1":
        return _validate_v1(envelope)
    if declared == "gallodoc-core/v3":
        return _validate_v3(envelope)
    return ValidationResult(
        valid=False,
        issues=[
            ValidationIssue(
                path="schema_version",
                message=f"unknown schema version {declared!r}",
            )
        ],
        schema_version=declared if isinstance(declared, str) else "",
    )


# ---------------------------------------------------------------------------
# Optional jsonschema-backed validation
# ---------------------------------------------------------------------------


def validate_with_jsonschema(envelope: dict[str, Any]) -> ValidationResult:
    """Full JSON-Schema validation when the ``jsonschema`` extra is installed.

    Dispatches by ``envelope["schema_version"]`` exactly like
    :func:`validate_envelope`. Falls back to the stdlib validator with a
    warning if the ``jsonschema`` extra is not installed.
    """
    try:
        import jsonschema  # type: ignore  # noqa: PLC0415
    except ImportError:
        result = validate_envelope(envelope)
        result.issues.append(
            ValidationIssue(
                path="$",
                message="jsonschema not installed — fell back to stdlib validator. Install with `pip install gallodoc[schema]` for full validation.",
                severity="warning",
            )
        )
        return result

    if not isinstance(envelope, dict):
        return ValidationResult(
            valid=False,
            issues=[ValidationIssue(path="$", message=f"envelope must be a JSON object, got {type(envelope).__name__}")],
        )

    declared = envelope.get("schema_version", "")
    if declared not in ("gallodoc-core/v1", "gallodoc-core/v3"):
        return ValidationResult(
            valid=False,
            issues=[
                ValidationIssue(
                    path="schema_version",
                    message=f"unknown schema version {declared!r}",
                )
            ],
            schema_version=declared if isinstance(declared, str) else "",
            used_jsonschema=True,
        )

    schema = load_schema(version=declared)
    issues: list[ValidationIssue] = []
    validator_cls = jsonschema.Draft202012Validator if hasattr(jsonschema, "Draft202012Validator") else jsonschema.Draft7Validator
    validator = validator_cls(schema)
    for err in sorted(validator.iter_errors(envelope), key=lambda e: list(e.absolute_path)):
        path = "$." + ".".join(str(p) for p in err.absolute_path)
        issues.append(ValidationIssue(path=path, message=err.message))
    _apply_execution_governance_public_safety_rules(envelope, issues)
    _apply_compliance_v12_public_safety_rules(envelope, issues)
    _apply_trust_decision_public_safety_rules(envelope, issues)
    _apply_v20_public_safety_rules(envelope, issues)
    if declared == "gallodoc-core/v3":
        _apply_v3_validator_rules(envelope, issues)
    return ValidationResult(
        valid=not issues,
        issues=issues,
        schema_version=str(envelope.get("schema_version", "")),
        used_jsonschema=True,
    )


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "load_envelope",
    "validate_envelope",
    "validate_with_jsonschema",
    "_validate_v1",
    "_validate_v3",
]
