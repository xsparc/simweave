# ADR 0017: descriptive sweep result review

Status: accepted

Date: 2026-10-22

SW019 follows merged sweep planning under delegated next-scope selection. Add a
pure summarize function and CLI that pair a strict Sweep with its exact SuiteReport.
Revalidate both models, reconstruct the plan and require complete Suite equality
and digest identity before grouping any results. Preserve scenario, adapter and
seed order from the plan; never pool distinct adapters or parameter points.

For each point/adapter, emit parameter values, seeds, passed/failed/error pair
counts and inherited comparison warnings. For complete points, summarize all four
metrics with baseline/candidate means and paired candidate-minus-baseline delta
mean/minimum/maximum. If any pair has an execution error, withhold all metric
aggregates for that point to avoid silently selecting surviving seeds. Other
complete points remain available. Preserve Suite review exit codes: 0 pass,
1 quality/regression failure, 2 execution or input failure.

Version-1 output binds the normalized sweep and source report with SHA-256 digests
and includes the existing Suite digest. CLI inputs are bounded to 64 KiB Sweep
and 4 MiB report; output is stdout or an exclusively created file. Validation
failure creates no output. Summary JSON is descriptive evidence, not a verified
recording, attestation, statistical confidence statement or optimization result.

Acceptance: exact parameter mapping, stable digests, arithmetic checks, pass/fail
counts, incomplete points, mismatched/mutated reports and plans, CLI schema/bounds/
non-overwrite, and real reference/MuJoCo execution. No simulation math, storage,
tenant authority, promotion or existing statistical classifier is changed.
