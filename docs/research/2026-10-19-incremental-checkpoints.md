# DirectionBriefV1: incremental checkpoints

- schema_version: 1
- baseline_commit: ea0726c
- scanned_at: 2026-10-19
- coverage: SW015 merge, earlier direction recommendations, maintenance/recovery,
  immutable artifact storage and SQLite backup semantics.

Finding: checkpoints currently retransfer every artifact under the maintenance
fence. The earlier incremental-recovery recommendation remains unimplemented.
[SQLite backup](https://sqlite.org/backup.html) supplies metadata snapshots, while
verified immutable objects can be retained independently of a failed snapshot.
source_event_date: undated living documentation, accessed 2026-10-19;
confidence: high; relevance: repeated large checkpoints;
direction_alignment: efficient reliable recovery; opportunity_or_risk: wasted
transfers versus stale/corrupt object reuse; engineering_cost: medium;
disposition: adopted under delegated scope selection; roadmap_delta: SW016;
verification_needed: 10 GiB baseline with approximately 1% new objects, transferred
byte accounting, three restart points, corruption rejection and complete restore.

Recommendation: opt-in local object cache with verified same-volume hard links,
fresh metadata every attempt and complete independently restorable checkpoints.
The browser, provider/distributed queue and calibration recommendations are already
delivered. Further simulator adapters need a named scenario and integration fixture.
Gaps: cache reuse reduces transfer and storage, not full integrity hashing or the
maintenance fence duration to zero. Cross-volume reuse, partial-object resume,
automatic pruning and PostgreSQL backups remain separate work.
