# CSV sweep export

Status: accepted, 2026-10-25.

## Decision

Add opt-in `sweep-review --format csv` with a fixed version-1 long-form header and four metric rows per parameter/adapter point. Recompute through the existing validated summary. Repeat parameters, seeds, counts, warnings, source hashes, exit code and descriptive-only interpretation on each row. Incomplete points keep all four rows but have blank metric values. Use Python CSV quoting for every cell and CRLF record endings; numeric values retain Python round-trip precision. Prefix arbitrary labels with literal text: and encode structured cells as JSON arrays/objects so exported text does not begin with spreadsheet formula characters. JSON remains the default; existing byte caps and exclusive output apply.

## Acceptance

Deterministic CSV parses to the expected row count and columns; numeric round trips, source hashes and seed ordering match the review; hostile labels remain text-prefixed; incomplete metrics are blank; CLI preserves CRLF and refuses overwrite or invalid evidence.

## Limits

CSV is a derived view, not telemetry verification, inference or baseline approval. Consumers must preserve the text: prefix or explicitly import those columns as text; editing or stripping it changes the safety boundary. No universal safety guarantee is made for all spreadsheet programs or subsequent save/reopen transformations. Missing numeric values mean incomplete evidence, never zero. JSON remains the authoritative structured review format.

