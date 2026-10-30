# Portable plan review

Status: accepted, 2026-10-31. SW027 implements the three SimWeave tasks in the
retained five-task handoff.

Allow the existing HTML renderer to opt into schema version 2. Add a scrollable
adapter table with before/after run and step counts and signed changes. Preserve
the v1 default byte output, global totals, source identities, escaping and hashed
script-free CSP. Use existing output bounds and exclusive file creation.

Add CSV selection to sweep-diff-verify. Read each input within 64 KiB, parse strict
UTF-8 CSV and compare both cells and exact bytes with a recomputed canonical
export. Require quoted fields, UTF-8 without BOM and CRLF; do not normalize or
repair modified evidence. Literal text: prefixes are part of the contract.
This intentionally rejects semantically similar spreadsheets saved in another
dialect. JSON verification remains unchanged.

Commit synthetic before/after plans that replace one adapter and one seed while
preserving total workload. Existing CI exercises v1/v2 JSON, v1/v2 HTML, CSV,
source verification and rejection with simulator execution forbidden. The added
adapters are planning declarations; their installations are unnecessary.

Verification proves only local source consistency, not authorship, execution,
physics identity or available runtime capacity. Source plans remain necessary
for future verification; a standalone review envelope is deferred.
