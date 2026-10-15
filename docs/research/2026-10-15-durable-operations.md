# Durable operations direction brief

schema_version: 1; scanned_at: 2026-10-15;
baseline_commit: 281b5b908872e48b1ce073d129db1f00b774ed3d.

Coverage: existing suite execution, run leases, immutable catalogs, artifact
verification, SQLite deployment boundaries and S3 publication semantics.

| Priority | Finding and source event date | Confidence / relevance / alignment | Opportunity, risk and cost | Disposition / roadmap delta / verification |
| --- | --- | --- | --- | --- |
| 1 | [S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html), living documentation checked 2026-10-15 | High; immutable evidence storage directly supports portable experiments | Avoid overwrite races with If-None-Match; incompatible servers must fail closed; medium integration cost | Adopt SW010; exercise conditional creation, digest validation, outage and recovery on a local S3-compatible server |
| 2 | [SQLite WAL](https://www.sqlite.org/wal.html), living documentation checked 2026-10-15 | High; directly constrains worker topology | Multiple local processes are supported; network filesystems are unsuitable; medium queue cost | Adopt SW010 with a single-host boundary; run four real processes and kill/recover one |

Overall recommendation: immutable artifact backends plus a separately leased suite
queue, retaining existing Suite and bundle contracts. Conservative retention
protects evidence; automated garbage collection and multi-host scheduling remain
out of scope. Evidence gaps before implementation: 1,000-object recovery and
100-job failure/cancellation behavior have not yet been measured.
