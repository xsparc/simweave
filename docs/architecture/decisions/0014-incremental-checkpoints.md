# ADR 0014: verified checkpoint object reuse

Status: accepted

Date: 2026-10-19

The maintainer delegated scope selection and requested next-milestone draft PRs.
SW016 selects recommendation 2 from the 2026-10-16 direction brief.

Add optional `--object-cache` to both checkpoint commands. Retain tenant-scoped,
digest-addressed objects only after full digest/size verification and atomic
publication. Verify cached contents on reuse; corrupt bytes fail closed. Link
verified cache objects into staging on the same volume. Every checkpoint retains
the complete version-1 manifest, metadata and object namespace. Restore still
copies and verifies into a fresh directory and starts paused.

Retries rebuild metadata under the existing maintenance fence, reuse complete
objects and repeat incomplete transfers. No stale metadata resume journal is used.
Report transferred bytes and reused objects. Cache paths cannot overlap the
artifact source, metadata, catalog or output, or traverse symlinks/junctions.
Operators must keep cached and checkpoint objects immutable: hard links share bytes.
Direct administrators remain outside the cooperative maintenance boundary.

Acceptance: 10 GiB fixture, approximately 1% new objects (rounded to whole objects),
only new bytes transferred on the successful incremental attempt, three restart
points, zero missing references and measured checkpoint/restore time. Unit tests
cover corrupt source/cache rejection, overlap, safe resume and standalone restore.
Portable CI runs the smaller physical-copy fixture plus the synthetic regressions.

Non-scope: retention deletion, partial-object resume, cross-volume copy fallback,
uncooperative writers, automatic resume, PostgreSQL-native recovery or deployment.
