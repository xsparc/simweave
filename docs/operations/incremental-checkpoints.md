# Incremental checkpoints

Supply `--object-cache backup-cache` to either `operations checkpoint` or
`operations maintenance checkpoint`. Use the same operator-owned cache for later
checkpoints on the same local volume. The maintenance form drains and stays paused
until explicit resume, including on failures. Quiesce legacy CLI writers and backend
administrators as with full checkpoints. PostgreSQL still requires native backup.

Each attempt takes fresh database snapshots. Objects already in the cache are
hashed and checked against metadata, then hard-linked into the checkpoint. Missing
objects are downloaded, verified, flushed and published atomically. A retry reuses
completed objects; it retransfers an interrupted object from the beginning.
The JSON result reports `transferred_bytes`, `reused_objects`, `transfer_seconds`
(including cache verification/linking) and total `seconds`.
Transferred bytes count complete source object reads during that successful attempt;
failed attempts and metadata copies are not included.

The output remains a complete version-1 checkpoint. It can be restored without the
cache or earlier checkpoints. Restore copies bytes into fresh state, verifies them,
and starts paused. A different-volume cache fails rather than silently copying
unchanged objects. Omitting the flag retains the full-copy path.

Treat cached and checkpoint objects as immutable. Hard links share storage, so
editing one path corrupts every linked copy; verification detects this but cannot
repair it. A local cache is not independent off-host disaster recovery. Keep an
independent backup for media loss. No cache deletion or retention policy is added.
Provision cache disk capacity explicitly; no aggregate cache-size quota is imposed.
Restrict cache access to the backup operator; concurrent hostile filesystem changes
are outside the supported boundary. Cache paths reject symlinks/junctions and source
or output overlap. Full integrity hashing and metadata locking still take time;
reduced transfer does not imply a fixed recovery-time guarantee.

Run `python scripts/check_operator_recovery.py --output .simweave/incremental --gib 10 --incremental`
for the synthetic volume drill. The output path must be new. CI uses a smaller
fixture; new-object fractions are rounded up to complete objects.
