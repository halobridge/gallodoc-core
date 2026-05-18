---
name: Schema question
about: Ask about the GalloDoc Core v1 schema — required vs optional sections, enum values, field semantics, vendor extensions.
title: "[SCHEMA] "
labels: question, schema
assignees: ''
---

> The schema is **frozen** at `gallodoc-core/v1`. The 17 required top-level
> sections and their inner fields are guaranteed stable. New behavior comes
> through the `extensions.<vendor>.*` namespace or via additive optional
> sections.
>
> Reference docs:
> * [`docs/gallodoc-core-v1.md`](../../docs/gallodoc-core-v1.md)
> * [`docs/gallodoc-units-v1.md`](../../docs/gallodoc-units-v1.md)
> * [`docs/gstp-v1.md`](../../docs/gstp-v1.md)
> * [`docs/GALLODOC_CORE_V1_FROZEN.md`](../../docs/GALLODOC_CORE_V1_FROZEN.md)

## Question

What part of the schema do you have a question about?

## Section / field path

e.g. `gallounits.units[].source_span`, `certification.status`,
`ai_usage.runs[].data_mode`, …

## Use case

What are you trying to model? (A short narrative is much better than a
generic question.)

## What you've already checked

Which docs / examples have you already read? Which existing example envelope
under `examples/` is closest to your use case?

## Additional context

Links, screenshots, anything else that helps maintainers answer quickly.
