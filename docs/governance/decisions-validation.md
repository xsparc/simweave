# SW007 regression decision validation

Date: 2026-10-14. Scope: ADR 0005, statistical summaries and immutable local baseline
history. Development started from squash-merged PR11, commit `a2337c1`.

## Verification procedure

- `python -m pytest`: existing contracts, service isolation and recording checks,
  plus exact/hand-calculated bootstrap cases, deterministic resampling, practical
  threshold boundaries, missing/mismatched/constant/small populations, quality
  gates, provenance, immutable records, concurrent approvals, rollback, corruption,
  quotas, public CLI and escaped script-free HTML.
- `python scripts/check_decisions_ci.py --output decision-check --source-revision COMMIT_SHA`:
  reference/MuJoCo positive and degraded controls, each 30 paired seeds. Recompute
  each decision and assert exact JSON equality. Import 20 independently recorded
  controller candidates, compare against approval 1, promote and roll back, then
  reopen/export history and verify all pinned digests and policies.
- In the ROS test image, run the same script with `--adapters gazebo --history-builds 0`.
  Verify every complete recording before statistical analysis.
- Run lint, formatting, static/detailed governance gates, source/wheel builds and
  installed package checks. Inspect generated reports using a loopback static
  preview and record browser errors without implying direct file-open validation.

## Current results

The full portable suite passed **163 tests**, including 34 decision/history tests.
All **16 live ROS/Gazebo conformance tests** passed. Ruff lint/format, static and
dated strict governance gates, source/wheel builds, and installed-wheel bundle
analysis, HTML generation and history export passed. The portable quickstart
executed 60 reference recordings and accepted both example policy metrics.

Each simulator completed separate positive and degraded 30-pair matrices (120
recordings per simulator). Every bundle's recordings were verified. Repeating
each seeded analysis produced identical JSON. RMSE results with tolerance 0.02 m:

| Adapter | Positive mean change / 95% interval (m) | Degraded mean change / 95% interval (m) |
| --- | --- | --- |
| Reference | -0.00109139 / [-0.00109363, -0.00108916] | +0.751905 / [0.751739, 0.752075] |
| MuJoCo | -0.00109104 / [-0.00109328, -0.00108881] | +0.751825 / [0.751660, 0.751995] |
| Gazebo | -0.00109104 / [-0.00109328, -0.00108881] | +0.751825 / [0.751660, 0.751995] |

All positive decisions returned 0; all degraded decisions returned 1 and preserved
30 candidate quality failures. Each adapter was analyzed separately. These results
do not establish general cross-engine equality or calibrated interval coverage.

All 20 independently recorded controller candidates (1,200 additional recordings)
retained approval 1's digest and policy. Promotion to generation 2, rollback to 3,
and reopening/exporting the 21-build catalog passed. No candidate import or compare
changed the approved baseline. The concurrency test allowed exactly one competing
approval and rejected the stale one.

Native execution used Linux x86_64, Python 3.12.3, MuJoCo 3.15.0 and the real ROS
Jazzy/Gazebo Harmonic fixture, non-root with networking disabled and resource limits.
The retained local image ID was
`sha256:8270b58df792b7f4508a16b1962a5c72c956d3c6ca07ac7cc9d837bca69280fe`.
Its installed code fingerprint was
`cfca2d7f2e2ccbd1064704358ac97cd96a61441b172f1046bd18c7783f9014ef`;
the supplied source label identified the base commit, with uncommitted development
captured by that fingerprint. After final metadata and degenerate-data refinements,
the final Windows CLI revalidated both native bundles and recomputed the same groups
and intervals twice. Its code fingerprint was
`3b2f4a97e40bd1f10458d53cb5c3edabe57ae8def41eb87a6d716792647c98bc`.
CI rebuilds the checked-out commit and repeats native and portable acceptance.
Existing ROS localhost-only and Starlette/httpx deprecation warnings remain.

Loopback browser previews displayed the positive decision, degraded MuJoCo result,
and all 20 history rows with three approval events. Browser warning/error logs were
empty. See [decision review](../assets/regression-decisions.jpg) and
[baseline history](../assets/baseline-history.jpg). Direct file-open was not tested.

A single local analysis measurement for 30 pairs, four metrics and 10,000
resamples took 0.196 seconds on Python 3.12.13. This excludes bundle verification,
simulation and disk I/O; it is an observation, not a latency guarantee.

## Scope limits

The 20 candidate artifacts use distinct controller tunings from one code revision;
they exercise build history, not twenty separate released binaries. Intervals
assume independent representative seeds, are approximate and marginal, and have
no multiple-testing or repeated-build correction. No empirical coverage claim or
human usability study is made. Catalog approval labels are synthetic in tests and
are unsigned operator assertions in the product. Original bundles require separate
retention. Hosted identity/authorization, multi-host storage and signed provenance
remain outside this slice. SW005/SW006 browser timing/file-open gaps remain unchanged.
