# ADR 0009: Connected review and coordinated recovery

Status: accepted

Date: 2026-10-15

The maintainer accepted recommendations 1 and 2 after PR15's squash merge.
Baseline: `01a4586910d22181e8065fe633b2c2998ee90382`.
SW011 connects suite artifacts to catalog review and adds operational metrics and
a coordinated recovery drill. Existing single-host scheduling and identity roles
remain authoritative.

Catalog uploads retain verified bytes before committing a build; failed catalog
commits may leave retained evidence, never a new dangling reference. Importers can
create a build from a completed same-tenant suite job. Catalog readers download
build bundles; run credentials download their job bundles. Downloads materialize
a bounded verified snapshot before responding, with bounded concurrency and cleanup.
Backend configuration is operator-only and shared by API and workers.

Persist fixed-name artifact failure counters and bounded worker heartbeat records.
Expose tenant-scoped queue/status metrics to run credentials and operator-wide
Prometheus text through the CLI. Never label metrics with tokens, subjects, job
IDs, object keys or tenant names. Worker freshness means heartbeat freshness,
not simulator correctness. Existing healthz remains a liveness check.

Coordinated checkpoints require a quiesced API/workers and reject running jobs.
Freeze queue, catalog and artifact metadata with write reservations, take online
SQLite snapshots, and copy all indexed bytes with digest verification. Validate
every completed-job/catalog reference. Publish a manifest only after all contents
are checked. Restore into a new directory, verify metadata hashes and every object,
and reject incomplete, corrupted or missing evidence. Never overwrite live state.
Credentials/backend endpoints are not included. These are trusted operator-local
backups, not untrusted catalog interchange or a substitute for signed archives.

Acceptance: 100 job-to-catalog-to-comparison flows across two tenants, automatic
upload retention, authenticated downloads and cross-tenant rejection; metrics for
queue age, worker freshness, lease loss and artifact errors; recover 1,000 bundles
and 100 jobs within five minutes with zero missing references. Test failed writes,
corruption, incomplete checkpoints, active-job refusal and download cleanup.

Expected paths: API/config/catalog/worker/artifacts, metrics/recovery modules, CLI,
tests, CI and evidence docs. Non-scope: multi-host scheduling, new identity roles,
automatic approvals, garbage collection, deployments and cloud provisioning.
Risks: external writers bypassing quiescence, disk capacity, stale heartbeats,
partial publication, backup tampering and backend outage.
