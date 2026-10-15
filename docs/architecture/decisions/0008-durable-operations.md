# ADR 0008: Immutable artifacts and leased suite jobs

Status: accepted

Date: 2026-10-15

The maintainer accepted recommendations 1 and 2 after PR14 was squash merged.
Baseline: `281b5b908872e48b1ce073d129db1f00b774ed3d`.

Store verified evidence bundles by tenant and SHA-256 through filesystem and
optional S3 backends. Publish bytes before indexing them. Reads verify size and
digest. Conditional creation prevents overwriting an existing object. Retention
is deliberately conservative: no deletion or garbage collection is exposed, so
job and catalog references cannot lose evidence through this service. Orphaned
objects after interrupted publication may be re-imported. Recovery copies indexed,
verified objects into a fresh backend; metadata uses SQLite's online backup API.
These are operator operations, with explicit configuration and credentials.

Add a separate versioned SQLite suite queue, with tenant scoping, idempotent
submission, bounded retention, atomic claims, lease renewal, cancellation and
attempt fencing. Expired work fails visibly; only an explicit retry requeues it.
Workers run complete bounded suites and publish immutable evidence before a
fenced completion update. Cancellation interrupts at sample boundaries; a blocked
adapter may finish later but cannot publish a successful job after losing its lease.
The engine remains unaware of scheduling and storage.

Four processes share a local filesystem database. This milestone does not claim
multi-host execution: SQLite WAL must not be placed on a network filesystem.
Storage portability is separate from scheduler scalability. Future distributed
claims can replace the queue without changing Suite or bundle contracts.

Acceptance: retain and recover 1,000 distinct valid bundles; execute 100 suite
jobs across four worker processes and two tenants; verify cancellation, killed
worker expiry, explicit retry, stale completion rejection, tenant isolation,
idempotency, corruption and backend failures. Exercise a real local S3-compatible
server, plus portable tests, lint, packaging and governance checks.

Expected paths: artifact/queue modules, CLI/API, suite cancellation hook, optional
S3 dependencies, tests, verification script and operations/evidence documentation.
Risks: disk exhaustion, backend outage, orphaned uploads, operator bucket lifecycle
rules, lost metadata and blocked adapters. No automatic retries, deletion, remote
code, arbitrary adapter registration, releases or production deployment.

Research: `docs/research/2026-10-15-durable-operations.md`.
