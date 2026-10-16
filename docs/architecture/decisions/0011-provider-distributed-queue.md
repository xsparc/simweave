# ADR 0011: Real provider integration and distributed suite scheduling

Status: accepted

Date: 2026-10-17

Baseline: `505b6195c2f2f654e1c7e014ad95b1f7ad6d9ba5`.
The maintainer approved recommendations 3 and 4 after PR17's squash merge.

SW013 adds an explicit Keycloak access-token profile alongside the strict default
RFC 9068 profile. Pin issuer, audience, authorized client, signature, lifetime,
subject mapping and role scope. Require Keycloak's signed Bearer token discriminator;
ID tokens remain invalid. Test an actual local provider with two tenants and three
roles, expiry, signing-key rotation and session/token revocation. Offline JWT
validation cannot instantly observe provider logout; document its bounded exposure.
No browser login or refresh-token persistence is added.

Add an optional PostgreSQL suite repository and shared artifact metadata, using
server-clock leases, transactional quota admission, SKIP LOCKED claims and attempt
fencing. Keep simulation independent of persistence. Workers use private scratch
space and the same operator-configured S3 backend; no network-mounted SQLite.
Existing SQLite deployments are not silently migrated. The catalog and legacy-run
stores remain local to a single API host. PostgreSQL backup is an operator-native
database procedure; the SQLite checkpoint command must reject distributed mode.

Acceptance: 1,000 jobs, eight worker processes across two network-separated worker
containers, two tenants, quotas, cancellation, worker loss and stale completion
rejection, measured claim latency, and immutable shared-object retrieval. This
single-machine container drill does not certify two physical hosts or database HA.
Keep backend choice explicit, connections bounded, errors sanitized and database
credentials in operator environment configuration. Use isolated synthetic services.

Expected paths: provider config/verifier, PostgreSQL repository and runtime factory,
artifact metadata boundary, API/CLI, integration fixtures, tests and CI, operations
and traceability. Risks: stale tokens, DB outage, transaction deadlocks, clock skew,
misconfigured shared storage and unsupported backup assumptions. Non-scope: live
migration/deployment, billing, new simulators, UI login, automatic retries or
baseline approvals, distributed catalog writes and PostgreSQL HA orchestration.
