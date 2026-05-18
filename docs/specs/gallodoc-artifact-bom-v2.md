# GalloDoc Artifact BOM — v2.0

**Schema slug:** `gallodoc.artifact_bom.v2.0`
**Top-level key:** `artifact_bom` (optional, additive)
**Master spec:** [`gallodoc-core-v2.0-master-spec.md`](gallodoc-core-v2.0-master-spec.md#11-artifact_bom)

A software / artifact bill-of-materials for any package GalloDoc
references — documents, models, skills, MCP tools, Python or npm
packages, containers, datasets. Field shapes overlap with widely used
SBOM formats so external SBOMs can be imported losslessly:

- [SPDX](https://spdx.dev/) — license / compliance focus.
- [CycloneDX](https://cyclonedx.org/) — vulnerability / security focus.

GalloDoc's projection is intentionally a small superset of common fields;
the open-core package itself ships **no live vulnerability database** and
**no malware payloads** — those stay in their upstream sources.

## Shape

```json
{
  "schema_version": "gallodoc.artifact_bom.v2.0",
  "components": [],
  "dependencies": [],
  "vulnerabilities": [],
  "licenses": []
}
```

## Object types

| Object | Purpose |
|---|---|
| `Component`     | `component_id`, `name`, `version`, `component_type` (`document`/`model`/`skill`/`mcp_tool`/`python_package`/`npm_package`/`container`/`dataset`), `hash`, `supplier_hash_or_id`, `purl`, `bom_ref`. |
| `Dependency`    | `dependency_id`, `from_component`, `to_component`, `relationship`. |
| `Vulnerability` | `vulnerability_id`, `component_ref`, `severity`, `source`, `advisory_ref`, `status`. |
| `License`       | `license_id`, `component_ref`, `license_name`, `license_hash_or_id`. |

## Privacy invariants

- Public examples use synthetic component names and hashes; no malware
  payloads, no live advisory bodies. Forbidden keys include
  `advisory_body`, `raw_advisory`, `exploit_payload`, `malware_payload`.
- Real advisory text remains in the upstream advisory source; this block
  stores only the reference (e.g. `OSV-2026-XXXXX`).

## Reference

- Minimal example: [`../../examples/v2_0/gallodoc_artifact_bom.json`](../../examples/v2_0/gallodoc_artifact_bom.json)
- Full reference: [`../../examples/v2_0/gallodoc_full_v2_reference.json`](../../examples/v2_0/gallodoc_full_v2_reference.json)
