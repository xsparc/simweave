# ADR 0015: bounded retained-artifact audit

Status: accepted

Date: 2026-10-20

SW017 follows incremental checkpoints under delegated next-scope selection.
Add an operator-only audit command for retained object integrity. Query one tenant
by ordered digest cursor, at most 25 objects (default 10), with one lookahead row.
Validate index metadata before object I/O. Download one bounded object at a time
to temporary storage and compare SHA-256 and size against the retained index.

Return version-1 JSON with per-object verified, corrupt, missing or unavailable
results, counts and a continuation cursor. Exit 0 for a healthy page, 1 for
observed failures, 2 for invalid inputs/metadata or command failure. Do not expose
raw backend diagnostics. S3 access/not-found/transport errors remain unavailable
because its existing adapter does not distinguish them reliably.

SQLite and PostgreSQL share the audit logic through tenant-scoped inventory pages.
Object I/O occurs outside database transactions. No mutation, repair, deletion,
approval, HTTP endpoint or scheduling automation is added. A page is an observation,
not a globally consistent snapshot. Concurrent inserts before the cursor can be
missed; pause writers for a fixed inventory or restart scans to include new objects.

Acceptance: clean and mixed-failure pages, tenant isolation, pagination without
duplicates, invalid bounds/metadata before I/O, fixed diagnostics, CLI exit codes,
unchanged retained metadata/objects, and PostgreSQL pagination integration coverage.
Byte integrity does not revalidate simulation semantics or signer provenance.
