# Next milestone: Connected, observable experiment operations

DirectionBriefV1; schema_version: 1; scanned_at: 2026-10-15;
baseline_commit: 281b5b908872e48b1ce073d129db1f00b774ed3d, plus the SW010 draft.
Coverage: current queue/artifact/catalog boundaries, deployment topology, identity,
operational diagnostics and statistical validity. These are advisory recommendations;
no new requirement, implementation, merge or deployment is authorized by this brief.

| Priority / direction | Target | Evidence / confidence / relevance and alignment | Cost and risk / disposition |
| --- | --- | --- | --- |
| 1. Connect artifacts to team review | Automatically retain catalog-imported ZIPs; authenticated tenant-scoped downloads; complete 100 job-to-catalog-to-comparison flows with zero cross-tenant reads | Current SW010 requires operator copy/import; [S3 conditional publication](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html), living source checked 2026-10-15. High confidence; removes a concrete usability gap | Medium; avoid cross-database partial publication. Adopt next, subject to approval |
| 2. Make operations observable and recoverable | Queue age, lease loss, artifact failures and worker health metrics; demonstrate a coordinated recovery of 1,000 bundles and 100 jobs within five minutes, with zero missing referenced evidence | Current backup is two quiesced snapshots; [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/), living source checked 2026-10-15. High confidence; supports reliable operations and vendor-neutral monitoring | Medium; metric cardinality and private data leakage. Adopt next, subject to approval |
| 3. Extend execution across hosts | Optional PostgreSQL claims; 1,000 jobs across eight workers on two hosts, verify lease loss and stale-worker rejection under connection failure | [PostgreSQL SELECT locking](https://www.postgresql.org/docs/current/sql-select.html), current docs checked 2026-10-15, supports SKIP LOCKED queue consumers. High confidence in architectural fit, medium in demand; extends scalability beyond SQLite | High; migration and distributed failure complexity. Monitor until multi-host operation is needed |
| 4. Validate service identity end to end | Reproducible Keycloak onboarding for two tenants and catalog roles, including expiry, key rotation and client revocation; design separate execution authority before enabling OIDC scheduling | [Keycloak service accounts](https://www.keycloak.org/docs/26.5.7/server_admin/index.html), checked 2026-10-15. Medium confidence; existing JWT boundary lacks real-provider onboarding | Medium; provider claims may differ from RFC 9068 requirements. Monitor; do not relax token validation implicitly |
| 5. Calibrate statistical decisions | Run 1,000 known-null/known-shift experiments; publish confidence coverage, false-positive rate and power by sample count/adapter, with predetermined acceptance bands | [SciPy bootstrap reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html), checked 2026-10-15. High confidence in need; protects scientific interpretation as job volume grows | Medium; simulation populations may not represent real robots. Monitor until test populations and acceptance bands are agreed |

Overall recommendation: prioritize 1 and 2 for the next bounded milestone. Preserve
the current single-host deployment while connecting the complete evidence workflow
and proving recovery. Targets above are proposed acceptance criteria, not measured
results. Evidence gaps: real multi-host throughput, live IdP interoperability,
full-sized artifact performance and empirical statistical calibration.
