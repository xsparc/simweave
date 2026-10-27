# Capacity export contracts

Status: accepted, 2026-10-27.

## Decision

Expose `sweep-capacity-schema` from the existing Pydantic contract and add `sweep-inspect --format csv`. Emit one quoted CSV row per adapter, including per-adapter counts, repeated whole-plan totals/headroom, evidence digests and interpretation. Prefix the free-text sweep name with text: and preserve UTF-8/CRLF. Centralize unchanged 64-run and 200000-step bounds in suites.py and reuse them for workload/capacity fields and arithmetic. Existing JSON values, HTML, byte bounds and exclusive file creation remain compatible.

## Milestone items

3. Publish the capacity JSON Schema.
4. Export capacity CSV for offline comparison.
5. Share admission limits across suite validation and capacity reports.

## Acceptance

Generated schema exposes closed nested contracts and shared limits. CSV round-trips hostile labels, sums adapter totals correctly, preserves identities/order and exact CLI bytes, and never overwrites files. Invalid and over-budget plans fail before output. Existing capacity boundary and full suite tests pass.

## Limits

CSV headroom is for the entire plan and is repeated on each adapter row; it is not per-adapter quota and must not be summed. Labels are deliberately prefixed; stripping the prefix can reintroduce spreadsheet formula risks. JSON Schema describes structure, not proof that a report derives from a valid plan. Reports remain unsigned planned counts, without execution, availability checks or resource estimates.
