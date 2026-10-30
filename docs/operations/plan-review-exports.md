# Review and verify plan comparisons

```console
simweave sweep-diff before.json after.json --schema-version 2 --output comparison.json
simweave sweep-diff-schema --schema-version 2
simweave sweep-diff before.json after.json --format csv --output comparison.csv
simweave sweep-diff-verify before.json after.json comparison.json
```

Default JSON and HTML remain version 1. Version 2 adds adapter_deltas ordered by
before adapters, then new after adapters. Every row has before/after run and
step counts, with zero for an absent adapter and after-minus-before deltas.
Each side sums to its global counts. CSV always exports v2, with a global row
followed by adapter rows; sum only the adapter rows. Names have a literal text:
prefix for spreadsheet import. Files and stdout preserve UTF-8/CRLF.

All three verifier inputs and comparison output are bounded to 64 KiB. Outputs
are created exclusively; source files and report evidence are never rewritten.
Verification accepts either supported version and requires all report fields
to match a newly computed comparison from the two sources. Success returns
verified=true with local_source_consistency_only; failure exits 2 with a fixed
sanitized diagnostic. It performs no simulation and proves no authorship,
signature, execution results or physics equivalence. Retain sources separately
if the comparison must remain independently checkable later.

Version 2 HTML is available with `--schema-version 2 --format html` and includes
adapter counts. CSV verification uses `sweep-diff-verify ... --format csv` and
requires exact canonical bytes. See the [portable example](portable-plan-review.md).
