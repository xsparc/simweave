# ADR 0006: Portable catalogs and tenant baseline permissions

Status: accepted

Date: 2026-10-14

The maintainer accepted recommendations 1 and 2 after PR12 was squash-merged.
Baseline: `401c0f3cc8fd97530aa503601e0c7cc1fcb11533`.

## Scope and decision

Export a consistent SQLite read transaction as versioned canonical NDJSON records,
with record digests and a final whole-stream digest. Bound records and total bytes;
do not deserialize SQL or extract filesystem paths. Restore into a new temporary
catalog, validate contracts, keys, generations and references, then publish without
overwriting an existing destination. Preserve original approval and comparison
digests. Archives contain reports, not original telemetry bundles; checksums detect
corruption, not forgery. Restore preserves historical statistical results rather
than rerunning inference under a different runtime.

Expose separate server-provisioned catalogs per tenant. Extend operator token
configuration with explicit principals and reader/importer/approver roles. Legacy
string mappings retain run permissions only. Catalog credentials have no run
mutation authority. Reader can inspect; importer can import verified evidence and
record comparisons; approver can append promotion/rollback events. Both write roles
can read, but neither implies the other. Derive tenant and approval identity from
configuration, never request bodies. Catalog restore remains an operator CLI action,
not an HTTP endpoint that can replace approval history.

Use bounded binary evidence uploads and fixed routes, with temporary files removed
after validation. Reuse existing catalog transactions and optimistic generation
checks. Single-host SQLite remains the deployment model; reverse proxy TLS, request
timeouts, rate limits and operator-controlled storage are required for remote use.

## Acceptance and verification

- Round-trip 100 builds with promotions, rollback and comparisons across Windows
  and Linux, preserving all record digests. Reject corrupt, truncated, oversized,
  reordered, duplicate and dangling-reference archives without publishing a DB.
- Exercise two tenants with all three roles, foreign labels, forbidden operations,
  spoofed identity, concurrent approvals, service restart and legacy token behavior.
- Provide public CLI commands and a standard-library API client example; validate
  OpenAPI, package installation, full portable suite, lint and governance.

Expected paths: archive/config/API/CLI modules, tests, portability script, examples,
CI, operations and governance. Risks: upload resource pressure, local operator
tampering, stale approvals, accidental cross-tenant access. Non-scope: OIDC, signed
archives, hosted deployment, new simulation engines, distributed jobs and UI.

Research: `docs/research/2026-10-14-team-evidence.md`.
