---
name: Bug report
about: Report a defect in gallodoc, the validator, the units engine, the AI usage helpers, or the GSTP verifier.
title: "[BUG] "
labels: bug
assignees: ''
---

> **Do not paste real PHI / PII into this issue.** Use synthetic envelopes
> from [`examples/`](../../examples) as the basis for reproductions. See
> [SECURITY.md](../../SECURITY.md). For security vulnerabilities, email
> `security@halobridge.ai` privately.

## Summary

One sentence describing what is broken.

## Expected behavior

What you expected to happen.

## Actual behavior

What actually happened (include error message and stack trace if any).

## Reproduction

Minimum steps to reproduce — ideally a single CLI command against a
synthetic example.

```bash
gallodoc validate examples/gallodoc_pdf_contract.json
```

If the bug needs a custom envelope, please attach a **synthetic** snippet:

```json
{
  "schema_version": "gallodoc-core/v1",
  "..."
}
```

## Environment

- `gallodoc --version` output:
- Python version:
- OS:
- Optional extras installed (`schema`, `tokenizer`, …):

## Additional context

Anything else maintainers should know.
