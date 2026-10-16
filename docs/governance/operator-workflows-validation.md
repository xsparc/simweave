# SW012 validation

Date: 2026-10-16. Baseline: `48474cba23b636d251f036597a0e5d8c1bdb8151`.

Local Windows, Python 3.12.13:

- Full regression suite: **290 passed**, including installed MuJoCo tests.
- Chromium 156 / Playwright 1.64: **30 workflow cases across two tenants**, plus
  six checks for invalid credentials, invalid JSON, cross-tenant import denial,
  keyboard tab order, discarded late responses after disconnect and mobile layout.
  No JavaScript page errors. Actual job and build downloads were byte-compared;
  uploaded bundles were accepted by the running API. This is automated browser
  evidence, not a screen-reader audit or Safari/Firefox certification.
- Four independent worker processes completed four active attempts while four
  follow-up jobs remained queued until explicit resume. Two tenants were used.
- Recovery fixture: **10,739,384,838 physical bytes** in **273 distinct bundles**,
  with **273 terminal job references**. Checkpoint **57.593 seconds**; fresh-directory
  restore **118.359 seconds**. All metadata and retained bytes were verified, with
  **zero missing references**. Pause persistence, failed-copy non-publication and
  post-publication interruption were exercised before successful restore/resume.
- Regression tests additionally cover cancelled workers still publishing, stale
  workers requiring explicit stopped acknowledgement, retry fencing, concurrent
  pause/resume reservations, catalog-write denial with continued reads, and failed
  restore verification without destination publication.
- Wheel and source distribution built successfully. All 13 new maintenance tests
  and the 30 browser cases plus six additional checks also passed against the
  installed wheel. The operator CLI checkpointed
  and restored six jobs, four objects and two catalogs; restored admission was
  paused until explicit resume.
- Ruff lint/format and static/current-date strict governance checks passed.

Reproduction: `scripts/check_browser_workspace.py`,
`scripts/check_operator_workers.py`, `scripts/check_operator_recovery.py`, and
`tests/test_operator_workflows.py`. Each drill emits a sanitized `verification.json`
under its fresh output directory. CI repeats browser/process drills on Windows and
Linux with a small recovery fixture. Full-volume timing is a local measurement,
not an SLA or a claim of CI/cloud throughput.

The volume fixture is ZIP_STORED evidence derived from one semantically verified
200,000-step suite, with unique ZIP dates and physical copies. Synthetic terminal
queue references exercise recovery at volume; this does not measure 273 executions.
The volume fixture has no catalog records; catalog/reference consistency also has
separate connected-operations regression coverage. The interruption tests model
process/workflow boundaries and injected copy errors, not hardware power loss.
No real OIDC provider, live ROS/Gazebo, or remote S3 service was rerun for SW012.
The existing S3 implementation is unchanged. Checkpoints still require cooperating
current-version local writers and enough capacity for full byte copies.
