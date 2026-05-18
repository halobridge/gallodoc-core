# Basic artifacts

`gallodoc.artifacts` ships a deterministic, regex-based extractor that
produces small typed artifact records linked back to GalloUnits.

> The extractor is a **starting point**. It does not claim production-grade
> accuracy and never promises perfect extraction. Anything labelled
> `needs_review=True` should be reviewed before downstream use.

## Artifact types

| Type | Trigger |
|---|---|
| `date` | ISO `YYYY-MM-DD`, `mm-dd-yyyy`, `mm/dd/yyyy`, or `Month dd, yyyy`. |
| `amount` | `$1,234.56`, `1234.56 USD`, `EUR 99.99`, etc. |
| `email` | RFC-style email pattern. |
| `phone` | Heuristic — at least 7 digits with separators. Always `needs_review`. |
| `reference_id` | `Invoice #...`, `PO ...`, `Ref ...`, `Claim ...`, `Tracking ...`. |
| `heading` | Classifier-tagged `heading` units, or ALL-CAPS lines. |
| `payment_terms` | `Net 30`, `Due on receipt`, `Payable within ...`. |
| `signature_block` | "Signed by ...", "Signature: ___", "/s/ ...". |
| `table_row` | Pipe- or tab-separated multi-column rows. |
| `line_item_candidate` | Bulleted or numbered list lines. |

## Output shape

```json
{
  "artifact_id": "art_<12-char-hash>",
  "artifact_type": "date",
  "source_unit_id": "gu_0003_a1b2c3",
  "fields": {"format": "iso"},
  "value_summary": "2026-04-30",
  "confidence": 0.85,
  "method": "regex_v1",
  "needs_review": false
}
```

* `source_unit_id` ties the artifact back to a GalloUnit so consumers can
  trace provenance.
* `method` is always `regex_v1` — downstream callers can tell that this is
  the open-core baseline, not a HaloBridge enterprise extractor.
* `needs_review` is true whenever the rule has known limitations (phone
  numbers, free-form dates, non-ISO amounts, etc.). Production pipelines
  should treat these as suggestions, not facts.

## Usage

```python
from gallodoc.artifacts import extract_basic_artifacts
from gallodoc.units import build_gallounits_block

text = open("sample.txt").read()
units = build_gallounits_block(text)["units"]
artifacts = extract_basic_artifacts(units)
for a in artifacts:
    print(a["artifact_type"], a["value_summary"], a["confidence"], a["needs_review"])
```

CLI:

```bash
gallodoc extract sample.txt --json | jq '.artifacts[] | {type: .artifact_type, value: .value_summary}'
```

## What the extractor will NOT do

* Parse semantics (e.g. "this date is the contract effective date").
* Normalize amounts to a single currency or precision.
* Localise dates beyond the patterns listed above.
* Disambiguate phone numbers from arbitrary digit strings.
* Run any third-party API.

If you need any of the above, treat this extractor as the starting layer
and stack a domain-specific extractor on top under
`extensions.<vendor>.artifacts.*`.

## Extending

Open-source contributions for new artifact types are welcome — keep them
deterministic and language-agnostic. ML-based or per-locale extractors
belong in HaloBridge or in a downstream package.
