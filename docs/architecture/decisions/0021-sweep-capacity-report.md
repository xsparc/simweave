# Sweep capacity report

Status: accepted, 2026-10-27.

## Decision

Extend `sweep-inspect` with opt-in `--format capacity-json` and `--format html`. Derive remaining run/step admission capacity and per-adapter totals from the validated workload preview. Preserve the default JSON contract and its schema command. HTML is a standalone escaped document with a hash-authorized inline stylesheet and restrictive CSP, with no scripts or remote assets. Existing 64 KiB input/output and exclusive output admission apply.

## Milestone items

3. Show remaining run and step admission capacity.
4. Aggregate planned runs and steps by adapter.
5. Export a standalone offline HTML capacity report.

## Acceptance

Remaining capacity reaches zero at each admission boundary; adapter totals equal workload totals in declared order. Default JSON is unchanged. Invalid/over-budget input produces no report, output never overwrites, hostile text is escaped, and contract constants reject non-integer values.

## Limits

Capacity is planned admission headroom, not reserved resources, adapter availability or a time/memory/storage/cost estimate. No simulation, queue scheduling or baseline decision occurs. Reports are unsigned derived evidence; execution independently validates its input.
