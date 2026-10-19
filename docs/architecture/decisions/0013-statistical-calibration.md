# ADR 0013: Synthetic statistical calibration

Status: accepted under delegated next-milestone selection, 2026-10-19.

Baseline: e360dfb. SW015 follows the earlier calibration recommendation and the
merged guided-review workflow. Provide an operator-invoked `calibrate` command
with versioned bounded configuration and JSON output. Generate independent
30-pair metric differences for normal null, normal threshold-boundary, normal
shifted and centered exponential null populations. Report all three verdict
frequencies, mean coverage, counts, Monte Carlo standard errors and input digests.
Use the existing percentile bootstrap and one shared classification function;
do not change the statistical algorithm or its approval semantics.

Acceptance: 1,000 trials per cohort, deterministic rerun equality, independent
exact/hand-calculated numeric checks, existing missing-pair/constant/singleton
and threshold-boundary tests, CLI rejection of unbounded work, full pytest,
lint/format and strict governance. Expected paths: calibration module/CLI, shared
classifier, tests, CI and interpretation/evidence documentation.

Risks: confusing synthetic rates with simulator performance, assuming normality,
ignoring dependence or multiple testing, and overinterpreting small samples.
No claim of calibrated real-world confidence, automatic promotion, new simulator,
bootstrap algorithm replacement, data upload or service endpoint. See the focused
research brief and operations/calibration.md for interpretation.
