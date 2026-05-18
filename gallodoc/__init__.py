"""GalloDoc Core v3 — open-core Python package.

Public entry points:

* :data:`GALLODOC_CORE_VERSION` — the active schema version string. As of
  this release, ``"gallodoc-core/v3"``. The v1 schema and validator remain
  parallel-supported for a 6-month deprecation window beginning
  2026-05-16; see :doc:`docs/specs/gallodoc-core-v3-master-spec.md`.
* :mod:`gallodoc.validation` — load the schema and validate envelopes.
  ``validate_envelope()`` dispatches by the envelope's declared
  ``schema_version``.
* :mod:`gallodoc.units` — normalize text, segment into GalloUnits, project
  per-model token counts, classify units.
* :mod:`gallodoc.ai_usage` — build and summarize AI usage ledger entries.
* :mod:`gallodoc.artifacts` — extract basic artifacts (dates, amounts, emails,
  phones, reference IDs, payment terms, line-item candidates).
* :mod:`gallodoc.gstp` — canonical-JSON hashing, manifest builder, and an
  offline verification shell. No signing service ships here.
* :mod:`gallodoc.markdown` — GalloMarkdown parser (``.gmd`` → GalloDoc).
* :mod:`gallodoc.markdown_renderer` — GalloMarkdown renderer (envelope → ``.gmd``).
* :mod:`gallodoc.conversion` — document conversion (txt/md/json/csv/html/pdf/...).
* :mod:`gallodoc.cli` — the ``gallodoc`` command-line interface.

This package never calls home, never stores raw prompts/responses by default,
and never includes private-key handling.
"""

from __future__ import annotations

GALLODOC_CORE_VERSION = "gallodoc-core/v3"
"""Active schema version string. v1 stays parallel-supported through the
6-month deprecation window beginning 2026-05-16."""

_MARKDOWN_SCHEMA_VERSION = "gallodoc-core/v1"
"""Schema version emitted by the GalloMarkdown authoring layer.

Stays pinned to v1 for v3.0 — the .gmd grammar emits the v1 envelope shape
(bare-array `relationships`, no required `trust` block). A future release
will land v3 GalloMarkdown emission alongside the existing v1 path. This
constant lets the markdown module declare the correct schema_version on
envelopes it emits without coupling .gmd output to bumps of
GALLODOC_CORE_VERSION."""

__all__ = ["GALLODOC_CORE_VERSION", "__version__"]

try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("gallodoc")
except Exception:
    __version__ = "unknown"
