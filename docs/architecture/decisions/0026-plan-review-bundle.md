# Plan-review bundle

Status: accepted under delegated stewardship, 2026-11-02.
Baseline: `1a23e05d2505dd467212b56aa0417aa9069d2d55`.

Implement the SimWeave SW028 handoff as one portable evidence slice: a closed
version-1 JSON envelope retains normalized before/after Sweep sources and their
version-2 plan comparison. Recompute the comparison on every intake; embedded
identities, totals and direction must match the retained sources. This proves
local consistency only, not authorship, runtime capacity or execution.

Use a 192 KiB total byte bound and 64 KiB bounds for each normalized source and
comparison. Reject duplicate JSON keys, unknown fields, unsupported/noninteger
versions, invalid plans and altered reports before output. Canonical export uses
sorted compact JSON plus LF; readers accept other JSON whitespace. All writes
are exclusive. No embedded path, URL, adapter installation or simulation executes.

Add schema, export, verify and HTML/CSV render commands. Reuse existing v2
renderers after envelope validation and preserve all two-source commands.
Acceptance covers deterministic round trips, tampered source/report/direction,
mutated models, duplicate keys, byte limits, fixed failure diagnostics, exclusive
output, the retained synthetic example and escaped offline HTML. Existing browser
layout evidence for the unchanged renderer remains applicable; no new layout is
introduced. Run focused/full tests, lint/format and static/strict governance.
