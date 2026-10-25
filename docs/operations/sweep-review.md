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

## Offline HTML review

```sh
simweave sweep-review sweep.json suite-report.json --format html --output review.html
```

Open the resulting file in a browser. It is self-contained, with no scripts or
external assets. Parameter/adapter sections show seeds, pass/fail/error counts,
warnings and descriptive metrics. Any execution error withholds that point's
metrics across all its seeds. Values display six significant digits; use the
default JSON output for full precision. Exit codes remain 0 for pass, 1 for
quality/regression failure and 2 for incomplete execution or invalid input.

The original sweep and suite report are revalidated and matched before writing;
existing output files are never overwritten. Source text is HTML-escaped and a
restrictive CSP permits only the fixed stylesheet. Evidence hashes identify the
normalized source contracts. This view does not verify raw telemetry, signatures,
physical accuracy or approve a baseline. See
[ADR 0018](../architecture/decisions/0018-offline-sweep-report.md).

## CSV export

```sh
simweave sweep-review sweep.json suite-report.json --format csv --output review.csv
```

The version-1 long-form CSV contains four metric rows per parameter/adapter point.
Columns include the sweep/scenario labels, adapter, parameters and seeds as JSON,
pass/fail/error counts, metric name and baseline/candidate/delta summaries, warnings
as JSON, all three evidence hashes, exit code and descriptive-only interpretation.
The header order is fixed by `sweep_csv.FIELDS`. Numeric values retain round-trip
precision. An incomplete point still has four rows, with blank numeric summaries;
blank means unavailable, never zero. Exit codes match JSON and HTML.

File and normal CLI stdout output use UTF-8 with CRLF records. All cells are quoted.
Arbitrary labels carry a literal `text:`
prefix; structured cells begin with a JSON object or array. This prevents source
labels from being emitted as formula-leading cells. Preserve the prefix when
opening in spreadsheets. For programmatic label recovery remove exactly the first
five characters after CSV parsing. Do not strip it and then reopen as untyped CSV.
Spreadsheet import and later editing can alter interpretation; no guarantee covers
all applications or subsequent transformations. JSON remains the structured
review format. Existing input caps and refusal to overwrite remain in force.
