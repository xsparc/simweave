# ADR 0027: Bundle source verification

Status: accepted
Date: 2026-11-05

## Context and decision

A standalone bundle check establishes internal consistency. Explicit before/after plans provide an independent comparison target: validate all models and recompute the full envelope, including canonical source identities. Replacing a whole envelope consistently still fails against different explicit plans. Whitespace and key order do not alter normalized plan identity; changed seeds and reversed direction do, even with unchanged workload counts.

```sh
simweave sweep-bundle examples/plan-review/before.json examples/plan-review/after.json --output bundle.json
simweave sweep-bundle-verify-sources bundle.json examples/plan-review/before.json examples/plan-review/after.json
simweave sweep-bundle-render bundle.json --format csv --output review.csv
simweave sweep-bundle-verify-csv bundle.json review.csv
```

Bundle intake remains bounded to 192 KiB, explicit plans and CSV to 64 KiB each. CSV verification requires the exact canonical UTF-8 bytes, CRLF, text prefixes and row order; it never repairs or writes evidence. SDK nested mutable models are revalidated. Both commands emit the existing fixed verification summary and return 2 on invalid input. These checks do not execute simulation, authenticate authorship or establish observed results. Keep source plans independently; replacing both sources and bundle defeats this local consistency check.

## Alternatives and consequences

Reject raw-byte-only comparison where normalized structured identity is intended. Do not silently repair retained evidence or treat local consistency as attestation. Reuse existing validated readers and exporters. Acceptance covers equivalent formatting, consistent replacement, reversal, bounds and read-only failure behavior.
