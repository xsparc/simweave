# Connected operations direction brief

DirectionBriefV1; schema_version: 1; scanned_at: 2026-10-15.
baseline_commit: 01a4586910d22181e8065fe633b2c2998ee90382 (PR15 squash). Coverage: catalog/artifact integration,
SQLite backup consistency, bounded operational metrics and existing tenant roles.

| Finding / source event date | Confidence, relevance and alignment | Opportunity / risk / cost | Disposition, roadmap delta and verification |
| --- | --- | --- | --- |
| [SQLite online backup](https://www.sqlite.org/backup.html), living documentation checked 2026-10-15 | High; recovery must include all metadata and bytes | Snapshot each database under a coordinated quiescent boundary; separate snapshots alone are insufficient; medium cost | Adopt SW011; verify references and fresh-target restore of 100 jobs/1,000 bundles |
| [Prometheus naming and labels](https://prometheus.io/docs/practices/naming/), living documentation checked 2026-10-15 | High; vendor-neutral operational visibility | Fixed names and low cardinality protect privacy and cost; medium cost | Adopt SW011; fixed counters, queue gauges, heartbeat freshness and tenant isolation tests |
| [S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html), living documentation checked 2026-10-15 | High; immutable evidence supports safe references | Publish verified bytes before catalog metadata; retain harmless orphans after failures; low incremental cost | Adopt SW011; automatic upload retention and 100 job-to-review flows |

Overall recommendation: connect existing stores without weakening role boundaries,
then prove coordinated recovery. Evidence gaps before verification: full flow count,
recovery duration and failure-path coverage. Future recommendations remain advisory.
