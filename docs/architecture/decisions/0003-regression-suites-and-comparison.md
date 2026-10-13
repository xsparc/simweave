# ADR 0003: Bounded regression suites and shared comparisons

Status: accepted

Date: 2026-10-13

The maintainer approved recommendations 1 and 2: regression suites/CI gates and
the comparison dashboard. SW005 delivers these as one coherent experiment-review
workflow, based on main at `0bdedee51f9c373f6e1cabf90402b5f81693cf02`.

## Decision and boundaries

Use a closed v1 suite contract containing scenarios, unique seeds, adapters,
baseline/candidate PD controllers, and optional absolute metric-increase limits.
Expand at most 64 runs and 200,000 total steps. Execute sequentially through the
existing streaming engine; never execute user code or silently skip an adapter.
Every case keeps its full portable recording. Reports contain bounded trajectory
previews, inputs, results, and sanitized execution errors. Write JSON and JUnit
even when individual runs fail. Exit 0 means all gates pass, 1 means quality
failure, and 2 means an execution/input error. An invalid baseline also fails CI.

Comparisons share one pure Python implementation. Only controller tuning and
display names may differ; seed, adapter, physics, target, sensors, disturbances,
and quality gates must match. Report signed candidate-minus-baseline metric
deltas, newly failing gates, and explicit regression limits. Do not infer
cross-engine equivalence or statistical significance. Runtime-version differences
are visible warnings. Full recordings, not plot previews, remain replay evidence.

The dashboard compares completed tenant-owned runs using a read-only API and
opens CLI suite reports through an authenticated validation endpoint. Opening a
report never imports runs, reads artifact paths, or executes simulations. Imported
reports are unsigned summaries, not verified recordings. Users select a suite
pair, navigate failed gates, and export the selected comparison as JSON. Existing
run recording export remains available. A file-size limit and closed bounded
models constrain report parsing. Other API bodies retain their existing limit.

This leaves queue quotas, persistence schema, and worker ownership unchanged.
Distributed suite scheduling, artifact storage, rerun bundles, worker routing,
performance optimization, and new robot fixtures are outside the approved slice.

## Acceptance

- Two controller configurations across ten seeds on both MuJoCo and Gazebo;
  good configurations pass, degraded control fails with exit 1 and JSON/JUnit.
- Execution failures produce exit 2 and per-case errors without suppressing
  other cases; no overwrite of existing output directories.
- Strict matrix bounds, duplicate rejection, normalized expansion, same-input
  comparisons, and tenant isolation are tested.
- Dashboard overlays baseline/candidate positions, shows every metric delta,
  highlights failed gates, selects the next failing gate, and exports a report.
- An observed browser walkthrough identifies and exports a known regression
  within two minutes after opening completed results. This is a workflow check,
  not a general usability study.
- Portable, live simulator, browser, packaging, and governance results are
  recorded separately with their actual limitations.

Research: `docs/research/2026-10-13-regression-workflows.md`.
