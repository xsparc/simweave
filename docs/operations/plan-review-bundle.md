# Portable plan-review bundle

Retain both normalized source plans and their version-2 comparison in one closed
version-1 JSON envelope. Verification recomputes the comparison from the retained
plans without simulation, adapter loading, network access or job submission.

```sh
simweave sweep-bundle examples/plan-review/before.json examples/plan-review/after.json --output review.bundle.json
simweave sweep-bundle-verify review.bundle.json
simweave sweep-bundle-render review.bundle.json --output review.html
simweave sweep-bundle-render review.bundle.json --format csv --output review.csv
simweave sweep-bundle-schema
```

Export emits sorted compact UTF-8 JSON plus LF. Intake accepts other JSON
whitespace but rejects duplicate keys, unknown fields, noninteger/unsupported
versions, invalid source plans, and comparisons that differ from recomputation.
The complete envelope is limited to 192 KiB and each normalized source/comparison
to 64 KiB. Reads are bounded before parsing. Rendered HTML/CSV retains the existing
64 KiB bound. Output files are created exclusively, after complete validation;
existing files and source files are preserved.

The before/after direction, normalized Sweep/Suite digests, and adapter ordering
remain meaningful even if global workload counts match. Retained plans are JSON
data; strings are never interpreted as paths or asset locations. HTML uses the
existing escaped, script-free v2 renderer and CSV retains text prefixes and CRLF.
Existing two-source comparison and verification commands remain available.

Successful verification reports only local source consistency. An attacker who
replaces both sources and their recomputed comparison can produce another valid
bundle. This is not signature verification, execution evidence, simulator
availability, numerical equivalence or baseline approval. Raw source-file byte
identity and formatting are not retained; identities describe normalized contracts.
