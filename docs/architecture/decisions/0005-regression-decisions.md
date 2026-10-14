# ADR 0005: Paired statistics and explicit baseline history

Status: accepted

Date: 2026-10-14

The maintainer approved statistical regression summaries and baseline history /
promotion after PR11's squash merge. Baseline: `a2337c1e4bfdbeb8de332efc494e456d3d174cdc`.

## Scope and decision

Add a pure, versioned decision layer over verified suite evidence. For each
scenario and adapter, pair identical seeds and physical inputs, sort by seed,
and bootstrap the mean candidate-minus-baseline metric difference. Use 5,000
seeded paired resamples by default, linear percentile endpoints, and a fixed
95% marginal interval. An explicit policy supplies practical absolute increase
tolerances in each metric's units. Keep the existing v1 suite/report unchanged.

A lower endpoint above tolerance means regression; an upper endpoint at or below
tolerance means within tolerance. Overlapping intervals, fewer than 30 complete
pairs, constant differences, missing runs, or runtime differences are explicitly
inconclusive. Quality-gate failures still fail. Never silently omit missing seeds,
pool simulators, claim exact coverage, or infer independence from unique seeds.
These intervals have no multiple-testing or repeated-build correction and cannot
automatically authorize a promotion. No new numerical dependency is needed.

Store immutable build snapshots in a separate local SQLite catalog. Import only
fully checked evidence bundles; retain the selected role's report, environment,
bundle digest, and content digest. The original full bundles remain separately
retained evidence. Build labels cannot be replaced. Explicit promotion records
the build, policy, operator-supplied approval label/reason, and timestamp. Rollback
appends an event restoring a previously approved build and its exact policy.
Generation checks and an immediate transaction prevent stale concurrent writes.
Comparisons pin an approval event, so later promotions cannot rewrite history.

The CLI exports versioned JSON plus self-contained HTML for statistics and history.
The catalog is single-host operator state, separate from the tenant-scoped service;
it exposes no HTTP mutation or Docker execution. JSON contracts form the future
service boundary. Local approval labels and checksums are not authentication or
signed attestations. Bound builds/events/comparisons, input sizes, and resampling.

## Acceptance and verification

- Analyze 30 paired seeds independently for reference, MuJoCo, and real Gazebo;
  reproduce seeded intervals, detect known degradation, and exercise noise.
- Verify constant, singleton, missing, mismatched, reordered, and threshold-edge
  inputs, plus independent exact/hand-calculated numerical checks.
- Import and compare 20 candidate builds against one explicitly promoted immutable
  baseline. Verify promotion, rollback, restart persistence, concurrent stale
  approval rejection, immutable labels, corruption detection, and bounded work.
- Exercise public CLI JSON/HTML output and package installation; run full portable
  tests, optional native checks, lint, formatting, static and dated governance gates.

Expected paths: statistics, catalog and report modules, CLI, tests, a native CI
verification script, examples, operations, architecture and governance docs.
Risks: bootstrap assumptions, repeated testing, untrusted evidence, stale approval,
local tampering and storage growth. Non-scope: hosted baseline management, identity,
signatures, automatic promotion, distributed execution, and new simulators.

Research: `docs/research/2026-10-14-regression-decisions.md`.
