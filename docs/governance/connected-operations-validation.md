# Connected operations validation

Date: 2026-10-15. Baseline: 01a4586910d22181e8065fe633b2c2998ee90382 (PR15 squash).
Scope: SW011 / ADR 0009, conversation-approved recommendations 1 and 2.

Initial Windows Python 3.12 acceptance completed 100 authenticated job-to-catalog-
comparison flows across two tenants, retained 1,000 distinct verified bundles and
restored all 100 jobs, catalog history and artifact references. Checkpoint plus
restore took 3.969 seconds, below the five-minute fixture target. Cross-tenant
reads and missing references were both zero. All 100 restored build downloads
and both tenants' comparison histories were checked. The small five-step reference
fixtures validate correctness, not production-scale throughput or statistical power.

Focused connected/catalog tests passed 34 checks covering retained uploads, job
imports, role/tenant download isolation, corruption, backend failure, cleanup,
metric privacy/freshness, active-job refusal, missing references, fresh-target
restore and incomplete/path-invalid manifests. Final checks are recorded below.

Limits: single-host SQLite, operator-quiesced recovery, trusted local checkpoints,
legacy catalog backfill required, best-effort artifact error counters if their
database is unavailable, no new live ROS or cloud provisioning. Windows/Linux
acceptance CI is tracked separately from local verification.

Final filesystem acceptance, with catalog history validation and worker reset,
recovered the complete fixture in 5.234 seconds. The real local S3 acceptance
also completed all 100 review flows and recovered 1,000 artifacts/100 jobs into
a fresh filesystem backend in 5.500 seconds, with zero missing references or
cross-tenant reads. It used the pinned RustFS image from SW010 with synthetic
credentials and loopback binding; the temporary server was removed afterward.

The full suite passed 277 tests, including installed MuJoCo checks. Ruff lint,
formatting, static and dated strict governance passed; wheel/source packages
built successfully. An earlier full run had only the temporary missing-ADR
registry failure, resolved before closeout. The pre-existing Starlette/httpx
deprecation warning remains; no new live ROS test is claimed.

The installed wheel passed all ten connected-operation tests. CLI Prometheus
metrics, coordinated checkpoint and fresh-target restore also passed against the
1,000-artifact/100-job fixture (1.782 and 1.829 seconds respectively).
