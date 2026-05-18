---
name: Feature request
about: Propose a new feature for gallodoc — a CLI command, a units helper, an artifact extractor, an optional plugin.
title: "[FEATURE] "
labels: enhancement
assignees: ''
---

> Reminder: `gallodoc-core/v1` is **frozen**. Required top-level sections,
> field types, and enum values do not change in v1. Additive changes
> (new optional sections, new optional fields, new artifact types, new
> tokenizer plugins) are welcome. Anything that requires breaking changes
> belongs on the v2 backlog. See
> [`docs/GALLODOC_CORE_V1_FROZEN.md`](../../docs/GALLODOC_CORE_V1_FROZEN.md).

## Problem

What use-case or workflow is awkward today?

## Proposed solution

What would you like to see? A concrete CLI command or Python API helps a
lot:

```bash
gallodoc <new-subcommand> ...
```

or

```python
from gallodoc.units import <new-helper>
```

## Alternatives considered

What other approaches did you weigh? Why this one?

## Compatibility

* Does this require a schema change? (If yes, it likely belongs in v2.)
* Does this require a new optional dependency? Which one?
* Does this affect the privacy invariants in `docs/privacy-and-safety.md`?

## Additional context

Links, references, prior art.
