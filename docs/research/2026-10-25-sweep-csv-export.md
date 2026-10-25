# DirectionBriefV1: CSV sweep export

- schema_version: 1
- baseline_commit: 5e8776d37ae5c6e0244e2b21f595d308dde595ff
- scanned_at: 2026-10-25
- coverage: merged milestone, roadmap, architecture, current CLI and library
  boundaries, regression tests, open draft status and primary platform guidance.

Finding: The existing JSON and HTML views do not provide a flat table for analysis tools. Python's CSV writer handles field quoting and record separation. OWASP warns that quoting alone does not stop formula interpretation and no single sanitizer covers all downstream consumers. A fixed schema with visibly prefixed labels preserves an explicit, reversible text boundary.

Source: [Python csv documentation](https://docs.python.org/3/library/csv.html) and [OWASP CSV Injection](https://community.owasp.org/attacks/CSV_Injection).
source_event_date: undated living documentation, accessed 2026-10-25;
confidence: high for the documented boundary, subject to local pinned-version tests;
relevance: csv sweep export; direction_alignment: portable verifiable workflows;
opportunity_or_risk: usable tabular evidence with an explicit spreadsheet text
boundary and visible incomplete observations; engineering_cost: low;
disposition: adopt; roadmap_delta: SW021;
verification_needed: Deterministic CSV parses to the expected row count and columns; numeric round trips, source hashes and seed ordering match the review; hostile labels remain text-prefixed; incomplete metrics are blank; CLI preserves CRLF and refuses overwrite or invalid evidence.

Overall recommendation: implement this bounded usability gap on current main.
Distributed recovery requires a larger state migration design and remains a
separate candidate. CSV export reuses the already validated sweep evidence model.
Evidence gaps: CSV is a derived view, not telemetry verification, inference or baseline approval. Consumers must preserve the text: prefix or explicitly import those columns as text; editing or stripping it changes the safety boundary. No universal safety guarantee is made for all spreadsheet programs or subsequent save/reopen transformations. Missing numeric values mean incomplete evidence, never zero. JSON remains the authoritative structured review format.

