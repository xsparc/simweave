# Interpreting statistical calibration

Run `simweave calibrate --trials 1000 --resamples 1000 --seed 1937` to print a
versioned JSON report. Trials are bounded to 1–1,000 per cohort and resamples to
1,000–5,000. No simulator, database, network access or approval is involved.
The default uses 1,000 resamples to bound experiment cost; ordinary decision
policies still default to 5,000. The report identifies the actual configuration.

Each of four cohorts uses 30 independent paired metric differences. Normal null
has mean and tolerance zero; normal boundary has mean and tolerance 0.1; normal
shifted has mean 1.0 and tolerance 0.1. Each has standard deviation 1.0. The
skewed null is exponential with rate one minus one, mean zero and tolerance zero.
The fixed bootstrap seed is 1729, matching the default decision policy. Generator
seeds are the supplied seed plus cohort index. Input digests identify exact draws;
repeatability is scoped to the Python/runtime implementation used for the run.

For null/boundary populations, the regression frequency is an observed false-positive
rate. For shifted populations it is observed detection power. Coverage counts how
often the interval contains the known population mean. All rates divide by every
trial, including inconclusive outcomes. A low false-positive rate can coexist with
many inconclusive results; do not interpret inconclusive as within tolerance.

Monte Carlo standard error is sqrt(p*(1-p)/trials), describing uncertainty in the
observed frequency only. It is not the uncertainty of an individual experiment.
Zero observed events do not prove zero risk; the plug-in standard error can also
be zero. Nominal 95% marginal coverage is not a guarantee of 95% observed coverage,
and a one-sided regression frequency is not the two-sided noncoverage frequency.

The synthetic differences test the interval/classifier, not physics or evidence
authenticity. They are not importable experiment bundles. Existing end-to-end tests
cover incomplete pairs, constant differences, too few seeds and mismatched runtime
or physics. Multiple metrics, repeated builds, correlated seeds, other sample sizes,
outliers and real simulator distributions need separate calibration. The command
does not recommend tolerances, certify a deployment or approve any baseline.
