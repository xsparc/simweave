# Review sweep results

After planning and running a sweep, group its results by parameter combination:

```sh
simweave sweep sweep.json --output suite.json
simweave suite suite.json --output results
simweave sweep-review sweep.json results/report.json --output review.json
```

Omit --output for JSON on stdout. Existing output files are never overwritten.
`sweep-review-schema` prints the closed version-1 result schema. Sweep input is
capped at 64 KiB and report input at 4 MiB. The report must contain exactly the
Suite reconstructed from the supplied Sweep, including case order and identities.
A mismatched or malformed input produces no review. Inputs are never modified.

Each point retains its scenario name, explicit axis values, adapter and seed order.
Passed/failed pairs follow the existing Suite comparison including baseline quality,
candidate quality and regression gates. Error pairs contain at least one failed
execution. Runtime-version and baseline warnings remain visible. Adapters and
parameter combinations are never averaged together.

For a complete point, each metric includes baseline_mean, candidate_mean and the
mean/minimum/maximum of paired candidate-minus-baseline deltas across seeds.
A positive delta means a larger metric value, not necessarily a failed gate: the
existing gate definitions determine failure. Any execution error makes that point's
metrics null; counts and warnings explain the incomplete evidence. Complete points
elsewhere in the grid are still summarized.

Exit 0 means all pairs passed, 1 means quality/regression failures, and 2 means
execution errors or invalid input/output. A valid report containing execution errors
still produces review JSON; an input/output failure prints a sanitized stderr error.
The Suite digest and hashes of normalized Sweep/SuiteReport data bind the source
contracts, not the formatting of input JSON. They are not signatures.

These are descriptive summaries. They do not rank an optimum, correct for multiple
comparisons, establish physical validity, or authorize baseline promotion. Report
validation checks structure and summary consistency, not the omitted full telemetry.
Use the existing bundle verifier and provenance workflow for those checks.
