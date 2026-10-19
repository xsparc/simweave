# SW015 calibration validation

The 2026-10-19 local run used 1,000 trials per cohort, 30 pairs, 1,000 bootstrap
resamples, generator seed 1937 and bootstrap seed 1729. The saved JSON contains
counts, rates, Monte Carlo standard errors and input digests.

| Cohort | Regression count | Regression frequency | Mean coverage |
| --- | ---: | ---: | ---: |
| Normal null | 34 / 1,000 | 3.4% false positives | 92.8% |
| Normal boundary | 27 / 1,000 | 2.7% false positives | 94.8% |
| Normal shifted | 999 / 1,000 | 99.9% power | 94.2% |
| Skewed null | 17 / 1,000 | 1.7% false positives | 91.0% |

These measured coverages are not uniformly 95%. In particular, the skewed-null
result illustrates undercoverage for this synthetic population and configuration.
Lower one-sided false positives do not imply better two-sided coverage. Preserve
the existing interpretation warnings; do not silently promote nominal confidence
to an observed guarantee. No statistical algorithm or approval policy was changed.

Targeted calibration/decision tests passed 46 cases, including independent exact
enumeration, frequency arithmetic, reproducibility, threshold equality, constant
differences and incomplete/too-small populations. The complete 4,000-trial JSON
report matched exactly on a second run. The full suite passed 309 tests, with
eight PostgreSQL integration tests skipped without a configured test DSN; installed
MuJoCo tests passed. Ruff lint/format, static/dated strict governance and wheel/source
builds passed. The existing Starlette/httpx deprecation warning remains. The isolated
offline build used the cached backend after the non-isolated environment lacked it.

Limits: synthetic independent differences, one local runtime and one fixed
bootstrap seed; no real simulator confidence calibration, multiplicity correction
or external statistical review. Cross-platform CI results are separate.
