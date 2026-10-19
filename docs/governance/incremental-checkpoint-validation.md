# SW016 verification

Synthetic tests cover two-tenant retained objects, new-object-only transfers,
checkpoint independence from cache names, restore into paused fresh state, three
interruption/retry points, corrupt cache/source rejection and path overlap.

The Windows volume drill retained 10,739,384,565 bytes in 273 initial objects,
then added three objects (1.099% churn after whole-object rounding). Its successful
incremental attempt transferred only 118,015,215 new bytes and reused all 273
initial objects. All 276 references restored; three interruption points left
admission paused and no references were missing.

Initial checkpoint: 183.172 seconds. Incremental checkpoint: 41.078 seconds.
Restore: 177.688 seconds. These are measured fixture intervals, not an SLA.
Admission remains paused after each checkpoint, so the checkpoint interval is
only the measured portion of operator downtime; explicit resume is separate.

A final-source recheck against the same retained fixture (a new cache seeded with
baseline hard links) again transferred exactly 118,015,215 bytes and reused 273
objects: transfer/verification/link phase 16.875 seconds, total checkpoint 48.031
seconds. This recheck includes the final queue-path overlap validation and phase
timing additions. See `incremental-checkpoint-sample.json` for both measurements.
The CI-size physical fixture also passed with the final code and timing output.

Final checks: 316 tests passed; eight PostgreSQL tests skipped without a disposable
DSN and one real symlink-creation test skipped because the host disallowed creation.
The overlap assertions preceding that skip passed. Linux CI exercises symlink
creation. Ruff checks/formatting, strict governance validation, wheel and source
distribution builds passed. The existing Starlette/httpx deprecation warning remains.

One earlier full run crossed a live helper-signature edit and failed with mixed
module versions. The complete suite was restarted against stable sources and passed.
The initial targeted run also caught Windows requiring a writable descriptor for
fsync; verified objects now open with r+b for flushing before publication.

Hard links require one volume and immutable operator-owned objects. Tests confirm
that mutation through a cache link is detected when verifying an older checkpoint;
the cache does not provide independent media-failure protection. No production,
PostgreSQL recovery, deployment or automatic cache pruning was exercised.
