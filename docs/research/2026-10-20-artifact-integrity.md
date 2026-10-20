# DirectionBriefV1: retained evidence integrity

- schema_version: 1
- baseline_commit: 32e518c
- scanned_at: 2026-10-20
- coverage: SW016 merge, artifact/recovery interfaces, operator workflows,
  SQLite/PostgreSQL metadata and primary S3 integrity guidance.

Finding: artifacts are verified on retrieval and checkpoint, but operators lack
a bounded diagnostic scan that continues after a damaged object. [S3 integrity
guidance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html)
describes checksum validation for stored and transferred data. SimWeave already
retains a SHA-256 identity, enabling backend-independent checks against its index.
source_event_date: undated living documentation, accessed 2026-10-20;
confidence: high; relevance: detect damaged evidence before recovery;
direction_alignment: reliable retained evidence; opportunity_or_risk: latent
corruption versus accidental repair/deletion; engineering_cost: medium;
disposition: adopt; roadmap_delta: SW017 operator audit;
verification_needed: scoped pagination, mixed failures, no source mutations and
sanitized output. Byte equality does not establish simulation or provenance validity.

Overall recommendation: a bounded, read-only audit is the next storage-operations
slice after incremental recovery. Automatic pruning needs separate destructive
policy; new simulators need a named scenario and fixture. Evidence gaps: no live
cloud scan is authorized or needed; PostgreSQL integration availability is reported
separately. Continuous-writer scans cannot claim a fixed global snapshot.
