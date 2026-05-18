"""GalloMarkdown / GalloMD — the human-readable authoring layer for GalloDoc.

This module compiles ``*.gmd`` files into valid GalloDoc envelopes.

Public entry points:

* :func:`parse_gallomd` — parse the raw text into a structured intermediate.
* :func:`gallomd_to_gallodoc` — compile straight to a GalloDoc envelope.
* :func:`validate_gallomd` — parse + safety check, raise on failure.

The companion module :mod:`gallodoc.markdown_renderer` performs the reverse
direction (envelope → ``.gmd``).

Spec: ``docs/specs/gallomarkdown-v1.md``.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from gallodoc import _MARKDOWN_SCHEMA_VERSION

GALLOMD_VERSION = "gallomarkdown/v1"


# ---------------------------------------------------------------------------
# Safety — shared between compile and render directions.
# ---------------------------------------------------------------------------


# Forbidden key names (case-insensitive). Any one of these as a block-body
# key, or as a YAML-style mapping key, is rejected at compile time.
FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        # raw model traffic
        "raw_prompt",
        "raw_response",
        "prompt_text",
        "response_text",
        "chain_of_thought",
        "cot_trace",
        "hidden_reasoning",
        "thought_chain",
        "scratchpad",
        # secrets / credentials
        "private_key",
        "bearer_token",
        "access_token",
        "refresh_token",
        "id_token",
        "oauth_token",
        "authorization",
        "client_secret",
        "api_key",
        "secret",
        "secret_value",
        "raw_secret",
        "credential",
        "credential_value",
        "credential_dump",
        "password",
        "jwt",
        "jwk",
        # weights / data
        "model_weights",
        "lora_weights",
        "adapter_blob",
        "training_payload",
        "fine_tune_dataset",
        "training_batch",
        "retrieval_chunk_body",
        "raw_chunk_text",
        "chunk_text",
        # PHI / PII
        "raw_phi",
        "phi_chunk",
        "ssn",
        "mrn",
        "patient_id",
        "patient_name",
        # raw queries / payloads
        "raw_sql",
        "sql_text",
        "raw_query",
        "raw_dialect_query",
        "raw_environment",
        "environment_variables",
        "env_vars",
    }
)

_JWTISH = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.")
_SSN_LIKE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
_PEM_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_OPENAI_KEYISH = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
_AWS_KEYISH = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GENERIC_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}\b")


def _scan_string_for_unsafe(value: str) -> str | None:
    """Return a short reason if the string is unsafe, else ``None``."""
    if _JWTISH.search(value):
        return "jwt_shaped_string"
    if _SSN_LIKE.search(value):
        return "ssn_literal"
    if _PEM_PRIVATE_KEY.search(value):
        return "private_key_pem"
    if _OPENAI_KEYISH.search(value):
        return "api_key_marker"
    if _AWS_KEYISH.search(value):
        return "aws_key_marker"
    if _GENERIC_BEARER.search(value):
        return "bearer_token_literal"
    return None


def _is_forbidden_key(key: str) -> bool:
    return key.strip().lower() in FORBIDDEN_KEYS


# ---------------------------------------------------------------------------
# Errors.
# ---------------------------------------------------------------------------


class GalloMDError(ValueError):
    """Raised when ``.gmd`` content is malformed or unsafe."""

    def __init__(self, message: str, *, line: int | None = None, reason: str = "") -> None:
        prefix = f"line {line}: " if line else ""
        super().__init__(f"{prefix}{message}")
        self.line = line
        self.reason = reason


# ---------------------------------------------------------------------------
# Intermediate representation produced by :func:`parse_gallomd`.
# ---------------------------------------------------------------------------


@dataclass
class GalloMDBlock:
    """A single ``::name ... ::`` fenced block from the source file."""

    name: str
    attrs: dict[str, str] = field(default_factory=dict)
    fields: dict[str, Any] = field(default_factory=dict)
    body_lines: list[str] = field(default_factory=list)
    line: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        # attrs win over body fields when both are set on the same key.
        if key in self.attrs:
            return self.attrs[key]
        return self.fields.get(key, default)


@dataclass
class GalloMDDocument:
    """Structured intermediate representation of a parsed ``.gmd`` file."""

    title: str = ""
    markdown_body: str = ""
    blocks: list[GalloMDBlock] = field(default_factory=list)
    headings: list[tuple[int, str]] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)

    def header(self) -> GalloMDBlock | None:
        for b in self.blocks:
            if b.name == "gallodoc":
                return b
        return None

    def blocks_by_name(self, name: str) -> list[GalloMDBlock]:
        return [b for b in self.blocks if b.name == name]


# ---------------------------------------------------------------------------
# Tokenizer / parser.
# ---------------------------------------------------------------------------


_BLOCK_OPEN = re.compile(r"^::(?P<name>[a-zA-Z][a-zA-Z0-9_]*)\s*(?P<attrs>.*)$")
_BLOCK_CLOSE = re.compile(r"^::\s*$")
_KV_LINE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<value>.*)$")
_HEADING_LINE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def _parse_attrs(raw: str) -> dict[str, str]:
    """Split ``key=value key2="v 2"`` into a dict."""
    out: dict[str, str] = {}
    s = raw.strip()
    i = 0
    while i < len(s):
        # skip whitespace
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s):
            break
        # read key
        j = i
        while j < len(s) and s[j] not in "= \t":
            j += 1
        key = s[i:j]
        if not key:
            break
        if j >= len(s) or s[j] != "=":
            # bare flag — store as "true"
            out[key] = "true"
            i = j
            continue
        # past '='
        j += 1
        # quoted value
        if j < len(s) and s[j] == '"':
            k = s.find('"', j + 1)
            if k == -1:
                raise GalloMDError(f"unterminated quoted attribute value for {key!r}")
            out[key] = s[j + 1 : k]
            i = k + 1
        else:
            k = j
            while k < len(s) and not s[k].isspace():
                k += 1
            out[key] = s[j:k]
            i = k
    return out


def _coerce_scalar(raw: str) -> Any:
    """Lightweight YAML-ish scalar coercion: bool, int, float, else string."""
    s = raw.strip()
    if s == "":
        return ""
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.lower() in ("null", "none", "~"):
        return None
    # integer
    if re.fullmatch(r"[+-]?\d+", s):
        try:
            return int(s)
        except ValueError:
            pass
    # float
    if re.fullmatch(r"[+-]?\d*\.\d+([eE][+-]?\d+)?", s):
        try:
            return float(s)
        except ValueError:
            pass
    # quoted string
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    # comma list
    if "," in s and not s.startswith("["):
        parts = [p.strip() for p in s.split(",") if p.strip()]
        if len(parts) > 1:
            return parts
    return s


_INDENTED_LIST_ITEM = re.compile(r"^(?P<indent>\s+)-\s+(?P<rest>.*)$")
_INDENTED_KV = re.compile(r"^(?P<indent>\s+)(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<value>.*)$")


def _parse_block_body(lines: list[str]) -> tuple[dict[str, Any], list[str]]:
    """Parse a block body into a key/value mapping plus trailing free-text.

    Recognises YAML-style continuations:

    ```
    key:
      - item1
      - item2

    key:
      sub_a: value
      sub_b: value
    ```

    Anything after a line that doesn't match the header pattern is treated
    as free-text and stored in ``body_lines``.
    """
    fields: dict[str, Any] = {}
    body_lines: list[str] = []
    in_body = False
    i = 0
    while i < len(lines):
        raw = lines[i]
        if in_body:
            body_lines.append(raw)
            i += 1
            continue
        if raw.strip() == "":
            i += 1
            continue
        m = _KV_LINE.match(raw)
        if m:
            key = m.group("key")
            value_text = m.group("value")
            if value_text.strip() == "":
                # peek ahead for a YAML continuation block.
                continuation, consumed = _consume_continuation(lines, i + 1)
                if continuation is not None:
                    fields[key] = continuation
                    i += 1 + consumed
                    continue
                fields[key] = ""
                i += 1
                continue
            fields[key] = _coerce_scalar(value_text)
            i += 1
            continue
        in_body = True
        body_lines.append(raw)
        i += 1
    while body_lines and body_lines[0].strip() == "":
        body_lines.pop(0)
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    return fields, body_lines


def _consume_continuation(lines: list[str], start: int) -> tuple[Any, int]:
    """Consume a YAML-style indented block starting at ``lines[start]``.

    Returns ``(value, consumed)`` where ``value`` is either a list, a dict,
    or ``None`` if no continuation is present.
    """
    if start >= len(lines):
        return None, 0
    first = lines[start]
    if first.strip() == "":
        # blank line right after the bare key — not a continuation.
        return None, 0
    list_m = _INDENTED_LIST_ITEM.match(first)
    if list_m:
        return _consume_list(lines, start)
    map_m = _INDENTED_KV.match(first)
    if map_m:
        return _consume_map(lines, start)
    return None, 0


def _consume_list(lines: list[str], start: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    consumed = 0
    base_indent: str | None = None
    i = start
    while i < len(lines):
        raw = lines[i]
        if raw.strip() == "":
            i += 1
            consumed += 1
            continue
        m = _INDENTED_LIST_ITEM.match(raw)
        if not m:
            break
        indent = m.group("indent")
        if base_indent is None:
            base_indent = indent
        elif len(indent) < len(base_indent):
            break
        items.append(_coerce_scalar(m.group("rest")))
        i += 1
        consumed += 1
    return items, consumed


def _consume_map(lines: list[str], start: int) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    consumed = 0
    base_indent: str | None = None
    i = start
    while i < len(lines):
        raw = lines[i]
        if raw.strip() == "":
            i += 1
            consumed += 1
            continue
        m = _INDENTED_KV.match(raw)
        if not m:
            break
        indent = m.group("indent")
        if base_indent is None:
            base_indent = indent
        elif len(indent) < len(base_indent):
            break
        key = m.group("key")
        value_text = m.group("value")
        if value_text.strip() == "":
            sub_value, sub_consumed = _consume_continuation(lines, i + 1)
            if sub_value is not None:
                out[key] = sub_value
                i += 1 + sub_consumed
                consumed += 1 + sub_consumed
                continue
            out[key] = ""
            i += 1
            consumed += 1
            continue
        out[key] = _coerce_scalar(value_text)
        i += 1
        consumed += 1
    return out, consumed


def parse_gallomd(text: str) -> GalloMDDocument:
    """Parse a ``.gmd`` source file into a :class:`GalloMDDocument`.

    Performs structural and safety checks but does **not** translate the
    blocks into a GalloDoc envelope yet — see :func:`gallomd_to_gallodoc`.
    """
    if not isinstance(text, str):
        raise GalloMDError("expected str")

    lines = text.splitlines()

    doc = GalloMDDocument()
    md_lines: list[str] = []
    cur_paragraph: list[str] = []
    in_block = False
    block_name = ""
    block_attrs: dict[str, str] = {}
    block_lines: list[str] = []
    block_start_line = 0
    in_code_fence = False
    code_fence_marker = ""

    def _flush_paragraph() -> None:
        if cur_paragraph:
            joined = " ".join(line.strip() for line in cur_paragraph if line.strip())
            if joined:
                doc.paragraphs.append(joined)
            cur_paragraph.clear()

    for idx, raw in enumerate(lines, start=1):
        # Triple-backtick code fence — preserve as-is, never interpret as a
        # GalloMD block.
        stripped = raw.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_code_fence:
                in_code_fence = True
                code_fence_marker = marker
            elif stripped.startswith(code_fence_marker):
                in_code_fence = False
                code_fence_marker = ""
            if in_block:
                block_lines.append(raw)
            else:
                md_lines.append(raw)
            continue
        if in_code_fence:
            if in_block:
                block_lines.append(raw)
            else:
                md_lines.append(raw)
            continue

        if in_block:
            if _BLOCK_CLOSE.match(raw):
                fields, body_lines = _parse_block_body(block_lines)
                block = GalloMDBlock(
                    name=block_name,
                    attrs=block_attrs,
                    fields=fields,
                    body_lines=body_lines,
                    line=block_start_line,
                )
                _check_block_safety(block)
                doc.blocks.append(block)
                in_block = False
                block_name = ""
                block_attrs = {}
                block_lines = []
                block_start_line = 0
                continue
            # nested ::name inside an open block is an error.
            m = _BLOCK_OPEN.match(raw)
            if m and not _BLOCK_CLOSE.match(raw):
                raise GalloMDError(
                    f"nested ::{m.group('name')} block before ::{block_name} closed",
                    line=idx,
                )
            block_lines.append(raw)
            continue

        # not in a block
        if _BLOCK_CLOSE.match(raw):
            raise GalloMDError("unexpected ::; no block is open", line=idx)
        m = _BLOCK_OPEN.match(raw)
        if m:
            _flush_paragraph()
            block_name = m.group("name").lower()
            attr_raw = m.group("attrs")
            try:
                block_attrs = _parse_attrs(attr_raw)
            except GalloMDError as exc:
                raise GalloMDError(str(exc), line=idx) from None
            for k in block_attrs:
                if _is_forbidden_key(k):
                    raise GalloMDError(
                        f"forbidden attribute {k!r} in ::{block_name} block",
                        line=idx,
                        reason="forbidden_key",
                    )
            block_lines = []
            block_start_line = idx
            in_block = True
            continue

        # Markdown content.
        md_lines.append(raw)
        h = _HEADING_LINE.match(raw)
        if h:
            _flush_paragraph()
            level = len(h.group(1))
            text_h = h.group(2).strip()
            doc.headings.append((level, text_h))
            if not doc.title and level == 1:
                doc.title = text_h
        elif raw.strip() == "":
            _flush_paragraph()
        else:
            cur_paragraph.append(raw)

    if in_block:
        raise GalloMDError(f"unterminated ::{block_name} block", line=block_start_line)

    _flush_paragraph()
    doc.markdown_body = "\n".join(md_lines).rstrip() + ("\n" if md_lines else "")
    return doc


def _check_block_safety(block: GalloMDBlock) -> None:
    """Reject blocks that contain forbidden keys or unsafe values."""
    for k, v in list(block.fields.items()):
        if _is_forbidden_key(k):
            raise GalloMDError(
                f"forbidden key {k!r} in ::{block.name} block",
                line=block.line,
                reason="forbidden_key",
            )
        _check_value_safety(v, block)
    for k in block.attrs:
        if _is_forbidden_key(k):
            raise GalloMDError(
                f"forbidden attribute {k!r} in ::{block.name} block",
                line=block.line,
                reason="forbidden_key",
            )
    body_text = "\n".join(block.body_lines)
    reason = _scan_string_for_unsafe(body_text)
    if reason:
        raise GalloMDError(
            f"unsafe content in ::{block.name} block body ({reason})",
            line=block.line,
            reason=reason,
        )


def _check_value_safety(value: Any, block: GalloMDBlock) -> None:
    if isinstance(value, str):
        reason = _scan_string_for_unsafe(value)
        if reason:
            raise GalloMDError(
                f"unsafe value in ::{block.name} block ({reason})",
                line=block.line,
                reason=reason,
            )
    elif isinstance(value, list):
        for item in value:
            _check_value_safety(item, block)
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and _is_forbidden_key(k):
                raise GalloMDError(
                    f"forbidden nested key {k!r} in ::{block.name} block",
                    line=block.line,
                    reason="forbidden_key",
                )
            _check_value_safety(v, block)


# ---------------------------------------------------------------------------
# Compilation: GalloMD → GalloDoc envelope.
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def _empty_envelope() -> dict[str, Any]:
    """Return a minimal, structurally-valid GalloDoc envelope skeleton."""
    return {
        "schema_version": _MARKDOWN_SCHEMA_VERSION,
        "profile": "open-core",
        "identity": {
            "gallodoc_id": "",
            "document_id": "",
            "title": "",
            "document_type": "",
            "mime_type": "text/markdown",
            "schema_version": _MARKDOWN_SCHEMA_VERSION,
            "source_schema_version": "gallodoc/v1",
            "created_at": "",
            "content_hash": "",
        },
        "source": {
            "source_system": "gallomarkdown",
            "source_kind": "markdown_authored",
            "source_record_id": "",
            "connector_slug": "gallomarkdown",
            "connection_id": "",
            "sync_run_id": "",
            "ingested_at": "",
            "readiness_status": "ready",
        },
        "purpose": {
            "primary_intent": "authoring",
            "workflow_intent": "gallomarkdown_authoring",
            "app_slug": "",
            "requested_by": "",
            "reason_code": "gallomarkdown_compile",
            "reason_text": "",
            "evidence": [],
            "confidence": 1.0,
        },
        "lifecycle": {
            "available": False,
            "current_status": "",
            "schema_version": "",
            "stages": [],
            "provenance_chain": [],
        },
        "activity": {
            "available": False,
            "event_count": 0,
            "counts_by_type": {},
            "latest_events": [],
        },
        "relationships": [],
        "evidence": {
            "count": 0,
            "refs": [],
        },
        "validations": {
            "contradictions": [],
            "packet_findings": [],
            "model_disagreements": [],
        },
        "security": {
            "phi_detected": False,
            "phi_categories": [],
            "phi_risk_level": "none",
            "encrypted": False,
            "encryption_backend": None,
            "encryption_key_id": None,
            "encrypted_fields": [],
            "masked_fields": [],
            "redaction_policy": None,
            "raw_export_allowed": True,
            "encryption_policy_status": "not_required",
            "last_phi_scan_at": None,
            "last_encrypted_at": None,
        },
        "exports": [],
        "extensions": {},
        "ai_usage": {
            "summary": {
                "total_runs": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "estimated_total_cost": 0.0,
                "currency": "USD",
            },
            "runs": [],
        },
        "gallounits": {
            "unit_strategy": "gallounit_v1",
            "canonical_text_hash": "",
            "units": [],
            "model_projections": [],
        },
        "certification": {
            "status": "none",
            "certification_type": "none",
            "certified_by": "",
            "certified_at": "",
            "policy_id": "",
            "policy_version": "",
            "case_id": "",
            "intent": "",
            "evidence_manifest_hash": "",
            "payload_hash": "",
            "signature_algorithm": "",
            "signature_id": "",
            "gstp_package_id": "",
            "revocation_status": "unknown",
            "revocation_reason": "",
        },
        "gstp": {
            "package_id": "",
            "package_type": "gallodoc_secure_transport_package",
            "status": "not_created",
            "payload_hash": "",
            "manifest_hash": "",
            "signature_algorithm": "",
            "signed_at": "",
            "signed_by_org": "",
            "verification_mode": "not_available",
            "contains": [],
            "verification_instructions": [],
            "public_key_reference": "",
            "cert_chain_reference": "",
        },
        "truth_ledger": {
            "available": False,
            "ledger_id": "",
            "current_snapshot_id": "",
            "authoritative_at": "",
            "claim_count": 0,
            "event_count": 0,
            "latest_event_hash": "",
            "snapshot_hash": "",
            "truth_state": "uncertified",
            "claims": [],
            "events": [],
        },
    }


def _str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def _maybe_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _apply_header(env: dict[str, Any], header: GalloMDBlock | None, default_title: str) -> None:
    if header is None:
        # Nothing declared — fall back to defaults that already live in
        # the envelope skeleton.
        if default_title:
            env["identity"]["title"] = default_title
        env["identity"]["document_type"] = env["identity"].get("document_type") or "gallomarkdown_document"
        env["identity"]["created_at"] = _now_iso()
        env["identity"]["gallodoc_id"] = env["identity"]["gallodoc_id"] or "gmd-" + hashlib.sha256(default_title.encode()).hexdigest()[:12]
        env["identity"]["document_id"] = env["identity"]["gallodoc_id"]
        return

    h = header
    schema_version = _str(h.get("schema_version", _MARKDOWN_SCHEMA_VERSION))
    if schema_version and schema_version != _MARKDOWN_SCHEMA_VERSION:
        # Authoring layer always emits the canonical version.
        schema_version = _MARKDOWN_SCHEMA_VERSION
    env["schema_version"] = schema_version

    doc_id = _str(h.get("doc_id") or h.get("document_id"))
    if not doc_id:
        seed = (default_title or "gallomarkdown_document").encode()
        doc_id = "gmd-" + hashlib.sha256(seed).hexdigest()[:12]
    title = _str(h.get("title") or default_title)
    doc_type = _str(h.get("document_type") or "gallomarkdown_document")
    mime = _str(h.get("mime_type") or "text/markdown")
    created_at = _str(h.get("created_at") or _now_iso())

    env["identity"].update(
        {
            "gallodoc_id": doc_id,
            "document_id": doc_id,
            "title": title,
            "document_type": doc_type,
            "mime_type": mime,
            "schema_version": _MARKDOWN_SCHEMA_VERSION,
            "created_at": created_at,
        }
    )

    env["source"].update(
        {
            "source_system": _str(h.get("source") or h.get("source_system") or "gallomarkdown"),
            "source_kind": _str(h.get("source_kind") or "markdown_authored"),
            "connector_slug": _str(h.get("connector_slug") or "gallomarkdown"),
            "ingested_at": _str(h.get("ingested_at") or created_at),
        }
    )

    confidence = _maybe_float(h.get("confidence"), default=1.0)
    env["purpose"].update(
        {
            "primary_intent": _str(h.get("primary_intent") or "authoring"),
            "workflow_intent": _str(h.get("workflow_intent") or "gallomarkdown_authoring"),
            "app_slug": _str(h.get("app_slug") or ""),
            "requested_by": _str(h.get("requested_by") or ""),
            "reason_code": _str(h.get("reason_code") or "gallomarkdown_compile"),
            "confidence": confidence if confidence is not None else 1.0,
        }
    )


def _block_to_record(block: GalloMDBlock) -> dict[str, Any]:
    record = dict(block.fields)
    for k, v in block.attrs.items():
        # attrs may also be coerced like body fields
        if k not in record:
            record[k] = _coerce_scalar(v)
    if block.body_lines:
        body = "\n".join(block.body_lines).strip()
        if body:
            record.setdefault("summary", body)
    return record


def _apply_artifacts(env: dict[str, Any], blocks: list[GalloMDBlock]) -> None:
    if not blocks:
        return
    artifacts = []
    for b in blocks:
        record = _block_to_record(b)
        family = _str(record.pop("family", "")) or "generic"
        art_id = _str(record.pop("id", "")) or f"art-{len(artifacts) + 1:04d}"
        artifacts.append({"id": art_id, "family": family, "data": record})
    env["extensions"].setdefault("gallomd_artifacts", []).extend(artifacts)


def _apply_evidence(env: dict[str, Any], blocks: list[GalloMDBlock]) -> None:
    if not blocks:
        return
    refs = env["evidence"].setdefault("refs", [])
    for b in blocks:
        record = _block_to_record(b)
        ev_id = _str(record.pop("id", "")) or f"ev-{len(refs) + 1:04d}"
        ref: dict[str, Any] = {"evidence_id": ev_id}
        if "source_ref" in record:
            ref["source_ref"] = _str(record.pop("source_ref"))
        if "hash" in record:
            ref["hash"] = _str(record.pop("hash"))
        if "summary" in record:
            ref["summary"] = _str(record.pop("summary"))
        # passthrough of any extra keys.
        for k, v in record.items():
            ref[k] = v
        refs.append(ref)
    env["evidence"]["count"] = len(refs)


def _ensure_trust_decision(env: dict[str, Any]) -> dict[str, Any]:
    block = env.get("trust_decision")
    if not isinstance(block, dict):
        block = {
            "schema_version": "gallodoc.trust_decision.v1.5",
            "trust_scores": [],
            "decision_gates": [],
            "policy_outcomes": [],
            "action_recommendations": [],
            "decision_receipts": [],
        }
        env["trust_decision"] = block
    block.setdefault("schema_version", "gallodoc.trust_decision.v1.5")
    for key in (
        "trust_scores",
        "decision_gates",
        "policy_outcomes",
        "action_recommendations",
        "decision_receipts",
    ):
        block.setdefault(key, [])
    return block


_TRUST_SUBJECT_TYPES = ("document", "packet", "execution", "agent_trace")
_TRUST_STATUS_BY_LEVEL = {
    "high": "trusted",
    "medium": "review_needed",
    "low": "review_needed",
    "blocked": "blocked",
}


def _normalise_grade(score: int, raw_grade: str) -> str:
    grade = (raw_grade or "").strip().upper()
    if grade in {"A", "B", "C", "D", "F"}:
        return grade
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _normalise_trust_status(raw_status: str, level: str) -> str:
    s = (raw_status or "").strip().lower()
    if s in {"trusted", "review_needed", "blocked", "insufficient_data"}:
        return s
    lvl = (level or "").strip().lower()
    return _TRUST_STATUS_BY_LEVEL.get(lvl, "review_needed")


def _default_trust_components(score: int, explanation: str) -> dict[str, Any]:
    """Trust scores require eight named component blocks. Default each to the parent score."""
    base = {
        "score": int(max(0, min(100, score))),
        "explanation": explanation or "Authored via GalloMarkdown — no detailed component breakdown supplied.",
    }
    return {
        "evidence_quality": dict(base),
        "lifecycle_completeness": dict(base),
        "security_posture": dict(base),
        "execution_governance": dict(base),
        "consent_custody_attestation": dict(base),
        "residency_training_model_risk": dict(base),
        "agent_observability": dict(base),
        "human_review": dict(base),
    }


def _apply_trust(env: dict[str, Any], blocks: list[GalloMDBlock]) -> None:
    if not blocks:
        return
    td = _ensure_trust_decision(env)
    for b in blocks:
        record = _block_to_record(b)
        score = record.pop("score", None)
        try:
            score_int = int(score) if score is not None else 0
        except (TypeError, ValueError):
            score_int = 0
        score_int = max(0, min(100, score_int))
        score_id = _str(record.pop("id", "")) or f"ts-{len(td['trust_scores']) + 1:04d}"
        subject_type = _str(record.pop("subject_type", "document")) or "document"
        if subject_type not in _TRUST_SUBJECT_TYPES:
            subject_type = "document"
        level = _str(record.pop("level", ""))
        explanation = _str(record.pop("explanation", "") or record.pop("summary", ""))
        components_raw = record.pop("components", None)
        if not isinstance(components_raw, dict) or not components_raw:
            components = _default_trust_components(score_int, explanation)
        else:
            components = _default_trust_components(score_int, explanation)
            components.update(
                {k: v for k, v in components_raw.items() if isinstance(v, dict) and "score" in v}
            )
        ts: dict[str, Any] = {
            "score_id": score_id,
            "subject_type": subject_type,
            "subject_id": _str(record.pop("subject_id", env["identity"].get("gallodoc_id", ""))) or "document",
            "score": score_int,
            "grade": _normalise_grade(score_int, _str(record.pop("grade", ""))),
            "status": _normalise_trust_status(_str(record.pop("status", "")), level),
            "calculated_at": _str(record.pop("calculated_at", env["identity"].get("created_at", ""))),
            "policy_version": _str(record.pop("policy_version", "")),
            "components": components,
        }
        if level:
            ts["level"] = level
        if explanation:
            ts["explanation_summary"] = explanation
        for k, v in record.items():
            ts[k] = v
        td["trust_scores"].append(ts)


_DECISION_ALIASES = {
    "approve": "allow",
    "approved": "allow",
    "allow": "allow",
    "allowed": "allow",
    "deny": "block",
    "denied": "block",
    "block": "block",
    "blocked": "block",
    "reject": "block",
    "rejected": "block",
    "warn": "warn",
    "warning": "warn",
    "review": "require_review",
    "require_review": "require_review",
    "needs_review": "require_review",
    "human_review": "require_review",
}


def _normalise_decision(raw: str) -> str:
    s = (raw or "").strip().lower()
    return _DECISION_ALIASES.get(s, s if s in {"allow", "warn", "block", "require_review"} else "require_review")


def _apply_decisions(env: dict[str, Any], blocks: list[GalloMDBlock]) -> None:
    if not blocks:
        return
    td = _ensure_trust_decision(env)
    for b in blocks:
        record = _block_to_record(b)
        gate_id = _str(record.pop("id", "")) or f"gate-{len(td['decision_gates']) + 1:04d}"
        action_raw = _str(record.pop("action", ""))
        decision_raw = _str(record.pop("decision", record.pop("action_decision", ""))) or action_raw
        gate: dict[str, Any] = {
            "gate_id": gate_id,
            "gate_name": _str(record.pop("gate_name", "gallomd_decision")),
            "action": action_raw or "review",
            "subject_type": _str(record.pop("subject_type", "document")) or "document",
            "subject_id": _str(record.pop("subject_id", env["identity"].get("gallodoc_id", ""))) or "document",
            "decision": _normalise_decision(decision_raw),
            "evaluated_at": _str(record.pop("evaluated_at", env["identity"].get("created_at", ""))),
            "policy_version": _str(record.pop("policy_version", "")),
        }
        confidence = _maybe_float(record.pop("confidence", None))
        if confidence is not None:
            gate["confidence"] = confidence
        reason = record.pop("reason", None)
        existing_codes = record.pop("reason_codes", None)
        codes: list[str] = []
        if existing_codes is not None:
            if isinstance(existing_codes, str):
                codes = [existing_codes] if existing_codes else []
            elif isinstance(existing_codes, list):
                codes = [str(c) for c in existing_codes]
        if reason is not None:
            if isinstance(reason, list):
                codes.extend(str(c) for c in reason)
            else:
                codes.append(str(reason))
        if codes:
            gate["reason_codes"] = codes
        for list_field in ("required_components", "blocked_conditions", "review_conditions"):
            if list_field in record:
                value = record.pop(list_field)
                if isinstance(value, str):
                    value = [value] if value else []
                gate[list_field] = list(value)
        if "summary" in record:
            gate["summary"] = _str(record.pop("summary"))
        for k, v in record.items():
            gate[k] = v
        td["decision_gates"].append(gate)


def _apply_policies(env: dict[str, Any], blocks: list[GalloMDBlock]) -> None:
    if not blocks:
        return
    td = _ensure_trust_decision(env)
    for b in blocks:
        record = _block_to_record(b)
        outcome_id = _str(record.pop("id", "")) or f"pol-{len(td['policy_outcomes']) + 1:04d}"
        outcome: dict[str, Any] = {
            "outcome_id": outcome_id,
            "policy_name": _str(record.pop("policy_name", "gallomd_policy")) or "gallomd_policy",
            "decision": _str(record.pop("decision", "")) or "allow",
            "policy_version": _str(record.pop("policy_version", "v1")) or "v1",
            "evaluated_at": _str(record.pop("evaluated_at", env["identity"].get("created_at", ""))),
        }
        if "summary" in record:
            outcome["summary"] = _str(record.pop("summary"))
        for k, v in record.items():
            outcome[k] = v
        td["policy_outcomes"].append(outcome)


def _ensure_agent_security(env: dict[str, Any]) -> dict[str, Any]:
    block = env.get("agent_supply_chain_security")
    if not isinstance(block, dict):
        block = {
            "schema_version": "gallodoc.agent_supply_chain_security.v1.6",
            "scans": [],
            "findings": [],
            "package_manifests": [],
            "permission_reviews": [],
            "dependency_reviews": [],
            "sandbox_observations": [],
            "llm_security_reviews": [],
            "quarantine_decisions": [],
            "install_receipts": [],
        }
        env["agent_supply_chain_security"] = block
    block.setdefault("schema_version", "gallodoc.agent_supply_chain_security.v1.6")
    for key in (
        "scans",
        "findings",
        "package_manifests",
        "permission_reviews",
        "dependency_reviews",
        "sandbox_observations",
        "llm_security_reviews",
        "quarantine_decisions",
        "install_receipts",
    ):
        block.setdefault(key, [])
    return block


def _apply_agent_security(env: dict[str, Any], blocks: list[GalloMDBlock]) -> None:
    if not blocks:
        return
    asc = _ensure_agent_security(env)
    for b in blocks:
        record = _block_to_record(b)
        finding_id = _str(record.pop("id", "")) or f"asc-find-{len(asc['findings']) + 1:04d}"
        finding: dict[str, Any] = {
            "finding_id": finding_id,
            "severity": _str(record.pop("risk_level", record.pop("severity", "low"))),
            "category": _str(record.pop("category", "agent_supply_chain_review")),
            "decision": _str(record.pop("decision", "review")),
            "summary": _str(record.pop("summary", "")),
        }
        risk_score = record.pop("risk_score", None)
        if risk_score is not None:
            try:
                finding["risk_score"] = int(risk_score)
            except (TypeError, ValueError):
                finding["risk_score"] = risk_score
        for k, v in record.items():
            finding[k] = v
        asc["findings"].append(finding)


def _apply_content(env: dict[str, Any], doc: GalloMDDocument) -> None:
    body = doc.markdown_body or ""
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    extensions = env["extensions"]
    extensions["gallomd_source"] = {
        "version": GALLOMD_VERSION,
        "markdown_hash": "sha256:" + body_hash,
        "heading_count": len(doc.headings),
        "paragraph_count": len(doc.paragraphs),
    }

    # Build GalloUnit candidates.
    units: list[dict[str, Any]] = []
    seq = 0
    for level, heading in doc.headings:
        seq += 1
        units.append(
            {
                "unit_id": f"u-h-{seq:04d}",
                "unit_type": "section",
                "semantic_role": "heading",
                "heading_level": level,
                "content_summary": heading[:240],
                "confidence": 0.95,
                "char_length": len(heading),
            }
        )
    for para in doc.paragraphs:
        seq += 1
        units.append(
            {
                "unit_id": f"u-p-{seq:04d}",
                "unit_type": "paragraph",
                "semantic_role": "content",
                "content_summary": para[:240],
                "confidence": 0.9,
                "char_length": len(para),
            }
        )
    env["gallounits"]["units"] = units
    env["gallounits"]["canonical_text_hash"] = "sha256:" + body_hash
    env["identity"]["content_hash"] = "sha256:" + body_hash


# Starter vocabulary for the ``::semantic_intent`` block. Tracks
# ``docs/specs/gallodoc-semantic-intent-v3.md``. The vocabulary extends
# additively in minor releases — values are added here in lockstep with
# the spec.
SEMANTIC_INTENT_VOCABULARY: frozenset[str] = frozenset({
    "invoice_to_employee_approver",
    "contract_supersedes_contract",
    "patient_to_consent_record",
    "claim_to_supporting_document",
    "case_to_case_continuation",
    "attachment_to_parent_document",
})


def _apply_semantic_intent(env: dict[str, Any], blocks: list[GalloMDBlock]) -> None:
    """Resolve ``::semantic_intent`` blocks to ``gallounits.units[].semantic_intent``.

    Block shape:

    .. code-block:: text

        ::semantic_intent
        unit_id: gu_017
        intent: invoice_to_employee_approver
        ::

    or the equivalent attribute form ``::semantic_intent unit_id=gu_017
    intent=invoice_to_employee_approver``. Unknown vocabulary values are
    rejected with :class:`GalloMDError`.

    Per Decision 5, the value lives at ``gallounits.units[].semantic_intent``
    on the unit whose ``unit_id`` matches. If the unit does not exist, a
    minimal placeholder unit is created so the intent survives.
    """
    if not blocks:
        return
    units = env.setdefault("gallounits", {}).setdefault("units", [])
    for b in blocks:
        record = _block_to_record(b)
        intent = _str(record.get("intent", "")).strip()
        unit_id = _str(record.get("unit_id", "")).strip()
        if not intent:
            raise GalloMDError(
                "::semantic_intent block missing required 'intent' field",
                line=b.line,
            )
        if intent not in SEMANTIC_INTENT_VOCABULARY:
            raise GalloMDError(
                f"::semantic_intent value {intent!r} is not in the published vocabulary "
                f"(see docs/specs/gallodoc-semantic-intent-v3.md)",
                line=b.line,
                reason="unknown_semantic_intent",
            )
        # Locate or create the target unit.
        target_unit: dict[str, Any] | None = None
        if unit_id:
            for u in units:
                if isinstance(u, dict) and u.get("unit_id") == unit_id:
                    target_unit = u
                    break
            if target_unit is None:
                target_unit = {
                    "unit_id": unit_id,
                    "unit_type": "intent_anchor",
                    "semantic_role": "intent_anchor",
                    "confidence": 0.9,
                }
                units.append(target_unit)
        else:
            # No unit_id — attach to the last unit if any; else create one.
            if units and isinstance(units[-1], dict):
                target_unit = units[-1]
            else:
                target_unit = {
                    "unit_id": f"u-intent-{len(units) + 1:04d}",
                    "unit_type": "intent_anchor",
                    "semantic_role": "intent_anchor",
                    "confidence": 0.9,
                }
                units.append(target_unit)
        target_unit["semantic_intent"] = intent


_BLOCK_DISPATCH: dict[str, str] = {
    "gallodoc": "header",
    "artifact": "artifact",
    "evidence": "evidence",
    "trust": "trust",
    "decision": "decision",
    "policy": "policy",
    "agent_security": "agent_security",
    "semantic_intent": "semantic_intent",   # NEW in v3 — Decision 5
}


def gallomd_to_gallodoc(text: str) -> dict[str, Any]:
    """Compile ``.gmd`` source to a GalloDoc envelope.

    Raises :class:`GalloMDError` on parse / safety failure.
    """
    doc = parse_gallomd(text)
    env = _empty_envelope()

    header = doc.header()
    _apply_header(env, header, doc.title)

    by_kind: dict[str, list[GalloMDBlock]] = {}
    for b in doc.blocks:
        kind = _BLOCK_DISPATCH.get(b.name)
        if kind is None or kind == "header":
            continue
        by_kind.setdefault(kind, []).append(b)

    _apply_artifacts(env, by_kind.get("artifact", []))
    _apply_evidence(env, by_kind.get("evidence", []))
    _apply_trust(env, by_kind.get("trust", []))
    _apply_decisions(env, by_kind.get("decision", []))
    _apply_policies(env, by_kind.get("policy", []))
    _apply_agent_security(env, by_kind.get("agent_security", []))

    _apply_content(env, doc)
    # semantic_intent (Decision 5) runs after _apply_content so unit_ids
    # generated for headings/paragraphs are available to match against.
    _apply_semantic_intent(env, by_kind.get("semantic_intent", []))
    return env


def validate_gallomd(text: str) -> GalloMDDocument:
    """Parse + safety-check a ``.gmd`` document.

    Returns the parsed document on success. Raises :class:`GalloMDError`
    on any parse, structural, or safety failure.
    """
    return parse_gallomd(text)


__all__ = [
    "GALLOMD_VERSION",
    "FORBIDDEN_KEYS",
    "SEMANTIC_INTENT_VOCABULARY",
    "GalloMDBlock",
    "GalloMDDocument",
    "GalloMDError",
    "parse_gallomd",
    "validate_gallomd",
    "gallomd_to_gallodoc",
]


# Re-export safety helpers so the renderer can reuse them.
def _public_safety_helpers() -> Iterable[tuple[str, Any]]:  # pragma: no cover
    return (
        ("scan_string_for_unsafe", _scan_string_for_unsafe),
        ("is_forbidden_key", _is_forbidden_key),
    )
