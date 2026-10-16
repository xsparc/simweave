# Provider/distributed validation

SW013 was verified on 2026-10-17 against the PR17 squash baseline
`505b6195c2f2f654e1c7e014ad95b1f7ad6d9ba5`.

The real Keycloak 26.4.7 fixture passed two tenants by three roles, run-authority
rejection, import/approval isolation, signing-key rotation with previous-key
retention, and actual access-token expiry. Both refresh-token revocation and
service-account logout made provider introspection inactive; offline API JWT
validation still returned 200 before expiry. This is documented behavior, not
immediate revocation. Human browser login was not tested.

The complete distributed fixture completed 1,000 jobs with eight worker processes
across two isolated worker containers and verified every retained S3 artifact.
Four killed-worker attempts expired, rejected stale completion and succeeded after
explicit retry. Global quota admission rejected excess work and cross-tenant job
reads returned no result. Successful claim latency was 6.617 ms median and
9.464 ms p95; execution/recovery was 29.454 seconds. Timing excludes setup and
artifact readback and measures this tiny reference fixture only. One physical
machine hosted all containers; two physical hosts and database HA are unverified.

PostgreSQL tests cover parallel idempotency, independent tenant keys, concurrent
claims, cancellation/stale attempts, database-clock leases, transactional quotas,
SKIP LOCKED, shared maintenance fencing and unsupported-checkpoint rejection.
The provider/distributed workflow repeats the real service drills using pinned
images and synthetic credentials, publishing only sanitized result JSON.

SQLite remains the default and its existing regression suite is retained. The
catalog remains a single API-host SQLite authority. PostgreSQL migration,
coordinated backup/restore, fair scheduling, arbitrary robot workloads and an
internet-facing production deployment are outside this slice.

The completed drill also restarted PostgreSQL, reopened the database, verified
persistent admission state and all job metadata, then downloaded a job artifact
through the API, rejected the other tenant, imported it into the catalog and
verified identical download bytes. The fixture refreshes Docker's dynamically
assigned host port after restart. An API lifecycle regression was found by this
drill and fixed using the application lifespan; a focused test verifies pool
closure and a sanitized storage-unavailable 503 response.

Final regression: **305 passed** including eight live PostgreSQL tests and installed
MuJoCo tests. Ruff lint/format, static and dated strict governance checks passed.
Wheel and source distribution built successfully. The only pytest warning is the
existing Starlette/httpx deprecation. ROS/Gazebo containers and browser automation
were not rerun for this backend slice; existing checks remain in CI. Remote CI
results are reported separately from local verification.
