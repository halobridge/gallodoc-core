"""GalloMarkdown renderer — render a GalloDoc envelope back to ``.gmd``.

This is the reverse direction of :mod:`gallodoc.markdown`. The compiled
JSON envelope remains canonical; rendering is a *projection* that strips
unsafe content and emits a human-readable Markdown file.

Public entry points:

* :func:`gallodoc_to_gallomd` — full renderer for an envelope.
* :func:`render_gallodoc_summary` — short, single-file overview block.
* :func:`render_gallodoc_section` — render a single named section.

The renderer never emits raw prompts/responses, raw secrets, raw PHI, or
chain-of-thought content — those are replaced with ``[REDACTED]`` and a
``::warning type=safety_redaction`` block is added at the top of the
file when any redaction occurred.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from gallodoc.markdown import (
    FORBIDDEN_KEYS,
    _is_forbidden_key,
    _scan_string_for_unsafe,
)

REDACTED = "[REDACTED]"


# Keys we want to surface in the rendered GalloMD header (in order).
_HEADER_KEY_ORDER: tuple[str, ...] = (
    "schema_version",
    "doc_id",
    "title",
    "document_type",
    "mime_type",
    "source",
    "source_kind",
    "connector_slug",
    "created_at",
    "primary_intent",
    "workflow_intent",
    "requested_by",
    "confidence",
)


# ---------------------------------------------------------------------------
# Safety helpers used in render direction.
# ---------------------------------------------------------------------------


class _RenderContext:
    """Tracks redactions made while rendering one envelope."""

    def __init__(self) -> None:
        self.redactions: list[str] = []

    def note(self, path: str, reason: str) -> None:
        self.redactions.append(f"{path}: {reason}")

    @property
    def had_redactions(self) -> bool:
        return bool(self.redactions)


def _safe_value(value: Any, *, ctx: _RenderContext, path: str) -> Any:
    """Walk ``value`` and replace forbidden keys / unsafe strings with ``[REDACTED]``."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            sub_path = f"{path}.{k}" if path else k
            if isinstance(k, str) and _is_forbidden_key(k):
                ctx.note(sub_path, "forbidden_key")
                out[k] = REDACTED
                continue
            out[k] = _safe_value(v, ctx=ctx, path=sub_path)
        return out
    if isinstance(value, list):
        return [_safe_value(item, ctx=ctx, path=f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, str):
        reason = _scan_string_for_unsafe(value)
        if reason:
            ctx.note(path, reason)
            return REDACTED
        return value
    return value


def _format_scalar(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        # Render a flat list of scalars as a comma-joined value.
        if all(isinstance(item, (str, int, float)) for item in value):
            return ", ".join(str(item) for item in value)
        # Fall back to repr — but trim quotes.
        return ", ".join(_format_scalar(item) for item in value)
    text = str(value)
    if any(ch in text for ch in ("\n", "\r")):
        text = text.replace("\n", " ").replace("\r", " ")
    return text


_KNOWN_LIST_FIELDS = frozenset(
    {
        "reason_codes",
        "drivers",
        "blockers",
        "warnings",
        "required_components",
        "blocked_conditions",
        "review_conditions",
        "matched_rules",
        "required_actions",
        "evidence",
        "limited_permissions",
        "approved_permissions",
        "denied_permissions",
        "requested_permissions",
        "declared_capabilities",
        "delegation_targets",
    }
)


def _render_kv(record: dict[str, Any], *, skip: Iterable[str] = ()) -> list[str]:
    skip_set = set(skip)
    lines: list[str] = []
    for key, value in record.items():
        if key in skip_set:
            continue
        if value in (None, ""):
            continue
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for sub_k, sub_v in value.items():
                if sub_v in (None, ""):
                    continue
                if isinstance(sub_v, dict):
                    lines.append(f"  {sub_k}:")
                    for inner_k, inner_v in sub_v.items():
                        if inner_v in (None, ""):
                            continue
                        lines.append(f"    {inner_k}: {_format_scalar(inner_v)}")
                else:
                    lines.append(f"  {sub_k}: {_format_scalar(sub_v)}")
            continue
        if isinstance(value, list):
            if not value:
                continue
            scalar_only = all(isinstance(item, (str, int, float, bool)) for item in value)
            # Always use the multi-line form for known list-shaped fields so
            # the round-trip preserves list semantics for single-element lists.
            if scalar_only and len(value) > 1 and key not in _KNOWN_LIST_FIELDS:
                lines.append(f"{key}: {_format_scalar(value)}")
                continue
            if scalar_only:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_format_scalar(item)}")
                continue
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    parts = [f"{k}={_format_scalar(v)}" for k, v in item.items() if v not in (None, "")]
                    lines.append("  - " + " ".join(parts))
                else:
                    lines.append(f"  - {_format_scalar(item)}")
            continue
        lines.append(f"{key}: {_format_scalar(value)}")
    return lines


def _render_block(name: str, attrs: dict[str, Any], record: dict[str, Any] | None) -> str:
    """Render a single ``::name [attrs]\\n... ::`` block."""
    parts: list[str] = []
    attr_pairs: list[str] = []
    for k, v in attrs.items():
        if v in (None, ""):
            continue
        text = _format_scalar(v)
        if any(ch.isspace() for ch in text):
            text = '"' + text.replace('"', "'") + '"'
        attr_pairs.append(f"{k}={text}")
    header = f"::{name}"
    if attr_pairs:
        header += " " + " ".join(attr_pairs)
    parts.append(header)
    if record:
        parts.extend(_render_kv(record))
    parts.append("::")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Section renderers.
# ---------------------------------------------------------------------------


def _render_header_block(envelope: dict[str, Any], ctx: _RenderContext) -> str:
    identity = envelope.get("identity") or {}
    source = envelope.get("source") or {}
    purpose = envelope.get("purpose") or {}

    raw = {
        "schema_version": envelope.get("schema_version") or "gallodoc-core/v1",
        "doc_id": identity.get("gallodoc_id") or identity.get("document_id") or "",
        "title": identity.get("title") or "",
        "document_type": identity.get("document_type") or "",
        "mime_type": identity.get("mime_type") or "",
        "source": source.get("source_system") or "",
        "source_kind": source.get("source_kind") or "",
        "connector_slug": source.get("connector_slug") or "",
        "created_at": identity.get("created_at") or "",
        "primary_intent": purpose.get("primary_intent") or "",
        "workflow_intent": purpose.get("workflow_intent") or "",
        "requested_by": purpose.get("requested_by") or "",
        "confidence": purpose.get("confidence"),
    }
    safe = _safe_value(raw, ctx=ctx, path="header")
    ordered = {k: safe[k] for k in _HEADER_KEY_ORDER if k in safe}
    return _render_block("gallodoc", attrs={}, record=ordered)


def _render_artifact_blocks(envelope: dict[str, Any], ctx: _RenderContext) -> list[str]:
    artifacts = (envelope.get("extensions") or {}).get("gallomd_artifacts") or []
    out: list[str] = []
    for art in artifacts:
        if not isinstance(art, dict):
            continue
        attrs = {
            "family": art.get("family") or "generic",
            "id": art.get("id") or art.get("artifact_id") or "",
        }
        body = _safe_value(art.get("data") or {}, ctx=ctx, path=f"artifact[{art.get('id', '?')}]")
        out.append(_render_block("artifact", attrs=attrs, record=body))
    # Also render basic extracted artifacts if present at top-level.
    legacy = (envelope.get("extensions") or {}).get("artifacts") or envelope.get("artifacts")
    if isinstance(legacy, list):
        for i, art in enumerate(legacy):
            if not isinstance(art, dict):
                continue
            attrs = {"family": art.get("artifact_type") or art.get("family") or "generic"}
            record = _safe_value({k: v for k, v in art.items() if k not in ("artifact_type", "family")},
                                 ctx=ctx, path=f"artifact_legacy[{i}]")
            out.append(_render_block("artifact", attrs=attrs, record=record))
    return out


def _render_evidence_blocks(envelope: dict[str, Any], ctx: _RenderContext) -> list[str]:
    evidence = envelope.get("evidence") or {}
    refs = evidence.get("refs") or []
    out: list[str] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        ev_id = ref.get("evidence_id") or ref.get("id") or ""
        attrs = {"id": ev_id} if ev_id else {}
        body = _safe_value(
            {k: v for k, v in ref.items() if k not in ("evidence_id", "id")},
            ctx=ctx,
            path=f"evidence[{ev_id or '?'}]",
        )
        out.append(_render_block("evidence", attrs=attrs, record=body))
    return out


def _render_trust_blocks(envelope: dict[str, Any], ctx: _RenderContext) -> list[str]:
    td = envelope.get("trust_decision")
    if not isinstance(td, dict):
        return []
    out: list[str] = []
    for ts in td.get("trust_scores") or []:
        if not isinstance(ts, dict):
            continue
        attrs = {
            "score": ts.get("score"),
            "level": ts.get("level") or "",
        }
        keep = {k: v for k, v in ts.items() if k not in ("score", "level")}
        body = _safe_value(keep, ctx=ctx, path=f"trust_decision.trust_scores[{ts.get('score_id', '?')}]")
        out.append(_render_block("trust", attrs=attrs, record=body))
    return out


def _render_decision_blocks(envelope: dict[str, Any], ctx: _RenderContext) -> list[str]:
    td = envelope.get("trust_decision")
    if not isinstance(td, dict):
        return []
    out: list[str] = []
    for gate in td.get("decision_gates") or []:
        if not isinstance(gate, dict):
            continue
        attrs = {
            "action": gate.get("action") or "",
            "id": gate.get("gate_id") or "",
        }
        confidence = gate.get("confidence")
        if isinstance(confidence, (int, float)):
            attrs["confidence"] = confidence
        keep = {k: v for k, v in gate.items() if k not in ("action", "gate_id", "confidence")}
        body = _safe_value(keep, ctx=ctx, path=f"trust_decision.decision_gates[{gate.get('gate_id', '?')}]")
        out.append(_render_block("decision", attrs=attrs, record=body))
    return out


def _render_policy_blocks(envelope: dict[str, Any], ctx: _RenderContext) -> list[str]:
    out: list[str] = []
    td = envelope.get("trust_decision")
    if isinstance(td, dict):
        for outcome in td.get("policy_outcomes") or []:
            if not isinstance(outcome, dict):
                continue
            attrs = {
                "decision": outcome.get("decision") or "",
                "id": outcome.get("outcome_id") or "",
            }
            keep = {k: v for k, v in outcome.items() if k not in ("decision", "outcome_id")}
            body = _safe_value(keep, ctx=ctx, path=f"trust_decision.policy_outcomes[{outcome.get('outcome_id', '?')}]")
            out.append(_render_block("policy", attrs=attrs, record=body))
    pg = envelope.get("policy_governance")
    if isinstance(pg, dict):
        for rule in pg.get("policy_rules") or []:
            if not isinstance(rule, dict):
                continue
            attrs = {
                "decision": rule.get("action") or "",
                "id": rule.get("rule_id") or "",
            }
            keep = {k: v for k, v in rule.items() if k not in ("action", "rule_id")}
            body = _safe_value(keep, ctx=ctx, path=f"policy_governance.policy_rules[{rule.get('rule_id', '?')}]")
            out.append(_render_block("policy", attrs=attrs, record=body))
    return out


def _render_semantic_intent_blocks(envelope: dict[str, Any], ctx: _RenderContext) -> list[str]:
    """Render units with a ``semantic_intent`` as ``::semantic_intent`` blocks.

    Decision 5 — the block round-trips through the renderer so authors
    can edit / replay intent assertions.
    """
    units = ((envelope.get("gallounits") or {}).get("units") or [])
    out: list[str] = []
    for u in units:
        if not isinstance(u, dict):
            continue
        intent = u.get("semantic_intent")
        if not intent:
            continue
        unit_id = u.get("unit_id") or ""
        record = {
            "unit_id": unit_id,
            "intent": intent,
        }
        body = _safe_value(record, ctx=ctx, path=f"gallounits.units[unit_id={unit_id}].semantic_intent")
        out.append(_render_block("semantic_intent", attrs={}, record=body))
    return out


def _render_agent_security_blocks(envelope: dict[str, Any], ctx: _RenderContext) -> list[str]:
    asc = envelope.get("agent_supply_chain_security")
    if not isinstance(asc, dict):
        return []
    out: list[str] = []
    for finding in asc.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        attrs = {
            "risk_level": finding.get("severity") or finding.get("risk_level") or "",
            "decision": finding.get("decision") or "",
            "id": finding.get("finding_id") or "",
        }
        keep = {k: v for k, v in finding.items() if k not in ("severity", "risk_level", "decision", "finding_id")}
        body = _safe_value(keep, ctx=ctx, path=f"agent_supply_chain_security.findings[{finding.get('finding_id', '?')}]")
        out.append(_render_block("agent_security", attrs=attrs, record=body))
    return out


# ---------------------------------------------------------------------------
# Public renderer entry points.
# ---------------------------------------------------------------------------


def gallodoc_to_gallomd(envelope: dict[str, Any]) -> str:
    """Render a GalloDoc envelope to GalloMarkdown text.

    Always returns valid GalloMD that can be compiled back via
    :func:`gallodoc.markdown.gallomd_to_gallodoc`.
    """
    if not isinstance(envelope, dict):
        raise TypeError("envelope must be a dict")

    ctx = _RenderContext()

    identity = envelope.get("identity") or {}
    title = identity.get("title") or identity.get("gallodoc_id") or "GalloDoc"
    doc_id = identity.get("gallodoc_id") or identity.get("document_id") or ""

    parts: list[str] = []
    # Avoid `# GalloDoc: GalloDoc: …` when the source title already has the prefix.
    title_emoji = "📄"
    if title.lower().startswith("gallodoc:"):
        parts.append(f"# {title_emoji} {title}".rstrip())
    else:
        parts.append(f"# {title_emoji} GalloDoc: {title}".rstrip())
    if doc_id:
        parts.append("")
        parts.append(f"> 🪪 **Document ID:** `{doc_id}`")

    # Reserve space for the warning block — we'll prepend it after we know
    # whether redactions happened.
    body_parts: list[str] = []
    body_parts.append("")
    body_parts.append(_render_header_block(envelope, ctx))

    purpose = envelope.get("purpose") or {}
    summary_text = purpose.get("reason_text") or ""
    body_parts.append("")
    body_parts.append("## 📝 Content")
    body_parts.append("")
    if summary_text:
        body_parts.append(_safe_value(summary_text, ctx=ctx, path="purpose.reason_text"))
    else:
        body_parts.append(_render_content_summary(envelope, ctx))

    artifact_blocks = _render_artifact_blocks(envelope, ctx)
    if artifact_blocks:
        body_parts.append("")
        body_parts.append("## 🔖 Artifacts")
        body_parts.append("")
        body_parts.extend(_join_blocks(artifact_blocks))

    evidence_blocks = _render_evidence_blocks(envelope, ctx)
    if evidence_blocks:
        body_parts.append("")
        body_parts.append("## 🧾 Evidence")
        body_parts.append("")
        body_parts.extend(_join_blocks(evidence_blocks))

    trust_blocks = _render_trust_blocks(envelope, ctx)
    if trust_blocks:
        body_parts.append("")
        body_parts.append("## 🎯 Trust")
        body_parts.append("")
        body_parts.extend(_join_blocks(trust_blocks))

    decision_blocks = _render_decision_blocks(envelope, ctx)
    if decision_blocks:
        body_parts.append("")
        body_parts.append("## ✅ Decisions")
        body_parts.append("")
        body_parts.extend(_join_blocks(decision_blocks))

    policy_blocks = _render_policy_blocks(envelope, ctx)
    if policy_blocks:
        body_parts.append("")
        body_parts.append("## 📜 Policy")
        body_parts.append("")
        body_parts.extend(_join_blocks(policy_blocks))

    agent_blocks = _render_agent_security_blocks(envelope, ctx)
    if agent_blocks:
        body_parts.append("")
        body_parts.append("## 🛡️ Agent Supply Chain Security")
        body_parts.append("")
        body_parts.extend(_join_blocks(agent_blocks))

    semantic_intent_blocks = _render_semantic_intent_blocks(envelope, ctx)
    if semantic_intent_blocks:
        body_parts.append("")
        body_parts.append("## 🧭 Semantic Intent")
        body_parts.append("")
        body_parts.extend(_join_blocks(semantic_intent_blocks))

    if ctx.had_redactions:
        warning = _render_warning_block(ctx)
        parts.append("")
        parts.append(warning)

    parts.extend(body_parts)
    rendered = "\n".join(parts).rstrip() + "\n"

    # Final defence: re-scan the rendered text. If anything unsafe survived
    # (it shouldn't, given _safe_value), redact the offending line.
    rendered = _final_redact(rendered, ctx)
    return rendered


def _join_blocks(blocks: list[str]) -> list[str]:
    """Insert a blank line between consecutive ``::`` blocks."""
    out: list[str] = []
    for i, block in enumerate(blocks):
        if i:
            out.append("")
        out.append(block)
    return out


def _render_content_summary(envelope: dict[str, Any], ctx: _RenderContext) -> str:
    identity = envelope.get("identity") or {}
    purpose = envelope.get("purpose") or {}
    parts: list[str] = []
    title = identity.get("title")
    if title:
        parts.append(f"**Title:** {_safe_value(title, ctx=ctx, path='identity.title')}")
    intent = purpose.get("primary_intent")
    if intent:
        parts.append(f"**Primary intent:** {_safe_value(intent, ctx=ctx, path='purpose.primary_intent')}")
    units = (envelope.get("gallounits") or {}).get("units") or []
    headings = [u for u in units if u.get("unit_type") == "heading_block"]
    if headings:
        parts.append("")
        parts.append("**Headings:**")
        for h in headings[:25]:
            level = h.get("heading_level") or 1
            summary = _safe_value(h.get("content_summary") or "", ctx=ctx, path=f"gallounits.units[{h.get('unit_id', '?')}]")
            parts.append(("  " * max(level - 1, 0)) + f"- {summary}")
    if not parts:
        parts.append(_safe_value(identity.get("title") or "(no rendered content)",
                                 ctx=ctx, path="identity.title"))
    return "\n".join(parts)


def _render_warning_block(ctx: _RenderContext) -> str:
    body = "⚠️ Unsafe content was redacted during GalloMD rendering."
    items = ctx.redactions[:8]
    if items:
        body += "\nredactions:\n"
        for item in items:
            body += f"  - {item}\n"
        if len(ctx.redactions) > 8:
            body += f"  - ... and {len(ctx.redactions) - 8} more\n"
    return f"::warning type=safety_redaction\n{body.rstrip()}\n::"


_LINE_REDACTOR_PATTERNS = (
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]*"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}\b"),
)


def _final_redact(rendered: str, ctx: _RenderContext) -> str:
    redacted = rendered
    for pattern in _LINE_REDACTOR_PATTERNS:
        if pattern.search(redacted):
            ctx.note("rendered_text", "post_render_pattern_match")
            redacted = pattern.sub(REDACTED, redacted)
    if ctx.had_redactions and "::warning type=safety_redaction" not in redacted:
        warning = _render_warning_block(ctx)
        # Insert warning right after the first H1.
        m = re.search(r"^(# [^\n]*\n)", redacted, re.MULTILINE)
        if m:
            insert_at = m.end()
            redacted = redacted[:insert_at] + "\n" + warning + "\n" + redacted[insert_at:]
        else:
            redacted = warning + "\n" + redacted
    return redacted


# ---------------------------------------------------------------------------
# Convenience helpers used by tests / CLI / Mvp services.
# ---------------------------------------------------------------------------


def render_gallodoc_summary(envelope: dict[str, Any]) -> str:
    """Render a short, single-block GalloMD overview of the envelope."""
    ctx = _RenderContext()
    identity = envelope.get("identity") or {}
    purpose = envelope.get("purpose") or {}
    title = identity.get("title") or "GalloDoc"
    parts = [f"# 📄 GalloDoc: {title}", ""]
    parts.append(_render_header_block(envelope, ctx))
    parts.append("")
    parts.append("## ✨ Summary")
    parts.append("")
    intent = purpose.get("primary_intent") or "unspecified"
    parts.append(f"- 🎯 **intent:** {intent}")
    parts.append(f"- 🪪 **doc_id:** `{identity.get('gallodoc_id') or identity.get('document_id') or ''}`")
    parts.append(f"- 🗂️ **document_type:** {identity.get('document_type') or ''}")
    counts_with_icons = (
        ("🧾", "evidence", len((envelope.get("evidence") or {}).get("refs") or [])),
        ("🎯", "trust_scores", len(((envelope.get("trust_decision") or {}).get("trust_scores")) or [])),
        ("✅", "decisions", len(((envelope.get("trust_decision") or {}).get("decision_gates")) or [])),
        ("🛡️", "agent_findings", len(((envelope.get("agent_supply_chain_security") or {}).get("findings")) or [])),
    )
    for icon, key, count in counts_with_icons:
        parts.append(f"- {icon} **{key}:** {count}")
    if ctx.had_redactions:
        parts.insert(2, _render_warning_block(ctx))
        parts.insert(3, "")
    return "\n".join(parts).rstrip() + "\n"


_SECTION_RENDERERS = {
    "header": lambda env, ctx: _render_header_block(env, ctx),
    "gallodoc": lambda env, ctx: _render_header_block(env, ctx),
    "artifacts": lambda env, ctx: "\n\n".join(_render_artifact_blocks(env, ctx)),
    "evidence": lambda env, ctx: "\n\n".join(_render_evidence_blocks(env, ctx)),
    "trust": lambda env, ctx: "\n\n".join(_render_trust_blocks(env, ctx)),
    "decisions": lambda env, ctx: "\n\n".join(_render_decision_blocks(env, ctx)),
    "policy": lambda env, ctx: "\n\n".join(_render_policy_blocks(env, ctx)),
    "agent_security": lambda env, ctx: "\n\n".join(_render_agent_security_blocks(env, ctx)),
}


def render_gallodoc_section(section_name: str, section_data: Any) -> str:
    """Render a single named section.

    ``section_data`` may be the full envelope (preferred) or just the
    section payload — the renderer adapts.
    """
    section_name = (section_name or "").strip().lower()
    ctx = _RenderContext()
    if section_name not in _SECTION_RENDERERS:
        raise ValueError(f"unknown section: {section_name!r}")
    if not isinstance(section_data, dict):
        raise TypeError("section_data must be a dict")
    if "schema_version" in section_data and "identity" in section_data:
        envelope = section_data
    else:
        # User passed only the inner block — wrap it in a minimal envelope.
        envelope = _wrap_inner_section(section_name, section_data)
    return _SECTION_RENDERERS[section_name](envelope, ctx)


def _wrap_inner_section(section_name: str, section_data: dict[str, Any]) -> dict[str, Any]:
    env: dict[str, Any] = {"identity": {}, "evidence": {"refs": []}, "extensions": {}, "purpose": {}}
    if section_name in ("trust", "decisions", "policy"):
        env["trust_decision"] = section_data
    elif section_name == "agent_security":
        env["agent_supply_chain_security"] = section_data
    elif section_name == "evidence":
        env["evidence"] = section_data
    elif section_name == "artifacts":
        env["extensions"] = {"gallomd_artifacts": section_data.get("gallomd_artifacts") or section_data}
    return env


__all__ = [
    "REDACTED",
    "FORBIDDEN_KEYS",
    "gallodoc_to_gallomd",
    "render_gallodoc_summary",
    "render_gallodoc_section",
]
