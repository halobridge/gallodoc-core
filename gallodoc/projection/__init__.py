"""Open-source reference projector for GalloDoc Core v3 envelopes.

This package ships the open-source field-stripping, enum-coercion,
cardinality-capping, and migration logic required to produce a valid
``gallodoc-core/v3`` envelope from richer producer-side input.

See ``docs/specs/gallodoc-core-v3-reference-projector.md`` for the
contract.
"""

from gallodoc.projection.projector import project_to_open_core
from gallodoc.projection.migrator import migrate_v1_to_v3

__all__ = ["project_to_open_core", "migrate_v1_to_v3"]
