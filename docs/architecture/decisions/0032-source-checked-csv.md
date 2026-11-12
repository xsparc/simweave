# ADR 0032: Source checked csv

Status: accepted
Date: 2026-11-12

## Decision


```sh
simweave sweep-bundle-verify-csv bundle.json review.csv --before before.json --after after.json --identity identity.json
```

CSV verification now accepts optional paired --before/--after plans, using the
same independent source check as HTML verification and rendering. Partial pairs,
reversal or wrong plans fail even when replacement evidence has a matching
identity. Identity records and expected digests remain mutually exclusive.
Calls without source options preserve standalone behavior. Exact CSV verification
still rejects edited bytes without normalization or repair.

Existing bounds remain: bundle 192 KiB, each source and CSV 64 KiB, identity 4096
bytes. Verification is read-only, emits fixed success JSON with exit 0, and uses
existing fixed diagnostics with exit 2 on failure. No simulation occurs. Matching
sources establish local consistency, not authorship or simulation equivalence.

## Alternatives and acceptance

Reuse existing bounded semantic readers and renderers rather than accepting unvalidated JSON or repairing exports. Acceptance covers closed contracts, strict versions, component/whole limits, independent source gates, replacement evidence, exact HTML/CSV bytes and read-only verification. No runtime authority or layout changes.
