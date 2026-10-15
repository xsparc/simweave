# Durable operations validation

Date: 2026-10-15. Baseline: 281b5b908872e48b1ce073d129db1f00b774ed3d.
Scope: SW010 / ADR 0008, accepted after PR14's squash merge.

Windows Python 3.12 acceptance script completed 100 actual suite jobs across
four spawned worker processes and two tenants. Filesystem worker counts were
19/27/28/26; the S3 run's queue counts were 27/23/22/28. Both runs terminated a
claimed worker process, observed lease expiry without automatic re-execution,
explicitly retried successfully and rejected the old claim's completion. Queued
cancellation prevented execution. Focused tests also cancel a running job during
artifact publication and verify its result remains cancelled.

Each run generated 1,000 distinct, valid, two-recording evidence bundles and
verified all recovered bytes against retained SHA-256/size metadata. Filesystem
workload completed in 34.672 seconds; S3 workload in 45.031 seconds. These are
small reference fixtures, not production throughput or large-bundle guarantees.
S3 storage was a real local RustFS 1.0.0 server, image digest
`sha256:8cc9801755448b71a786705ce76692c77e14936cccd87cf2fc31842e58f4d1ff`.
Conditional duplicate publication, object reads and recovery were exercised;
no cloud account or production data was used. Metadata backup and restored-index
reads were verified. Corruption, invalid ZIPs, tenant isolation, idempotency
conflicts, exhausted retry allowance and publication failures have focused tests.

The first complete suite ran 262 passing tests and one governance failure because
the new accepted ADR did not yet have its derived registry entry. This document
and the registry complete that traceability. Final checks are recorded below.

Limitations: single-host scheduling, conservative indefinite retention, no automatic
catalog ZIP ingestion, no multi-host or paid-cloud verification, and no new ROS
fixture. Existing simulator contracts are unchanged. Recovery needs intact source
bytes plus independently retained metadata. Windows/Linux CI runs the acceptance
script; its results must be checked separately from local evidence.

Final local checks: 267 tests passed (including installed MuJoCo tests), Ruff lint
and formatting passed, dated strict governance passed without warnings, and
wheel/source distributions built successfully. The pre-existing Starlette/httpx
deprecation warning remains. No new ROS live validation was required or claimed.

Final S3 acceptance also routed all four suite workers directly through S3: counts
25/26/26/23, total workload 63.797 seconds, 1,000 bundles recovered. A deliberately
corrupted synthetic object was rejected on reads and conditional publication; only
the test operator repaired it. Fourteen focused tests passed against the installed
wheel. Documented CLI submit/worker/list/backup commands passed; the example suite
reported exit code 2 for its unavailable simulator rather than masking it as a
scientific pass.
