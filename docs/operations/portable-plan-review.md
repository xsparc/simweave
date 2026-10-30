# Portable plan-review example

Run from the repository root after installing SimWeave:

```console
simweave sweep-diff examples/plan-review/before.json examples/plan-review/after.json --output comparison-v1.json
simweave sweep-diff examples/plan-review/before.json examples/plan-review/after.json --schema-version 2 --output comparison-v2.json
simweave sweep-diff examples/plan-review/before.json examples/plan-review/after.json --format csv --output comparison.csv
simweave sweep-diff examples/plan-review/before.json examples/plan-review/after.json --format html --schema-version 2 --output comparison.html
simweave sweep-diff-verify examples/plan-review/before.json examples/plan-review/after.json comparison-v1.json
simweave sweep-diff-verify examples/plan-review/before.json examples/plan-review/after.json comparison-v2.json
simweave sweep-diff-verify examples/plan-review/before.json examples/plan-review/after.json comparison.csv --format csv
```

The plans remove gazebo, add mujoco and change a seed; total run and step counts
stay equal, while identities differ. No simulator is installed or invoked by
these commands. The test suite forbids execution during this acceptance workflow.

Version 2 HTML adds per-adapter counts; default HTML remains version 1. Tables
scroll within their container on narrow screens. Both preserve fixed CSP and
escaped labels. HTML is a human review artifact, not accepted by the verifier.

CSV verification requires the exact exported UTF-8/CRLF bytes, quoted fields,
column/row order and literal text: prefixes. Spreadsheet resaving, BOM insertion,
newline conversion, extra rows or changed cells fail verification. Both source
plans and the report are bounded to 64 KiB. Verification is read-only and emits
local_source_consistency_only. Swap the two source arguments to see a rejected
direction, or modify a retained CSV and observe exit 2 with no repaired output.

Output creation is exclusive. Keep source plans with their report for later
checks. Equal workload is not equivalent experimentation; even verified evidence
does not establish authorship, execution, available engines or physics agreement.
