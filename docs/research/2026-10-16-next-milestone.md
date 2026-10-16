# DirectionBriefV1: guided review and efficient recovery

- schema_version: 1
- baseline_commit: 48474cba23b636d251f036597a0e5d8c1bdb8151
- scanned_at: 2026-10-16
- coverage: SW012 local verification, browser review usability, SQLite recovery,
  identity-provider interoperability, multi-host scheduling and statistical practice.

These are advisory recommendations after SW012, not approved requirements.
The targets below are proposed acceptance criteria, not completed measurements.

1. **Guided baseline approval and decision review.** Add explicit approver-only
   promotion/rollback, generation-conflict handling and readable metric summaries
   to the workspace. Target: **20 approval/rollback/conflict cases across two tenants**,
   a **30-paired-seed** review fixture, keyboard confirmation and immutable audit events.
   [W3C dialog focus guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
   informs confirmation behavior; explicit approval remains a project decision.
   source_event_date: undated living documentation, accessed 2026-10-16;
   confidence: high; relevance: complete reviewer workflow;
   direction_alignment: ease of use; opportunity_or_risk: accidental promotion;
   engineering_cost: medium; disposition: monitor; roadmap_delta: none until accepted;
   verification_needed: role isolation, stale-generation rejection and keyboard tests.
2. **Resumable, incremental checkpoints.** Reuse verified immutable objects and
   resume interrupted copies without deleting retained evidence. Target: a
   **10 GiB fixture with 1% churn**, copying only new object bytes, **three restart
   points**, zero missing references and measured pause/transfer/restore time.
   [SQLite backup](https://www.sqlite.org/backup.html) provides metadata snapshots;
   object reuse and resume need their own verified application protocol.
   source_event_date: undated documentation, accessed 2026-10-16;
   confidence: high; relevance: measured full-copy cost;
   direction_alignment: performance and portability;
   opportunity_or_risk: stale manifests or unsafe reuse; engineering_cost: high;
   disposition: monitor; roadmap_delta: none until accepted;
   verification_needed: corruption detection, bounded resume state and full restore.
3. **Real identity-provider integration.** Validate catalog access with local
   Keycloak before adding login UX. Target: **two tenants, three roles**, expiry,
   signing-key rotation and logout/revocation semantics with documented offline-JWT
   limits. [Keycloak OIDC endpoints](https://www.keycloak.org/securing-apps/oidc-layers).
   source_event_date: undated living documentation, accessed 2026-10-16;
   confidence: high; relevance: current synthetic-only provider verification;
   direction_alignment: SaaS interoperability; opportunity_or_risk: revocation assumptions;
   engineering_cost: medium; disposition: monitor; roadmap_delta: none;
   verification_needed: real provider/token behavior and explicit issuer policy.
4. **Multi-host scheduling.** Design a PostgreSQL queue boundary before migrating.
   Target: **1,000 jobs, eight workers across two hosts**, fenced completion under
   worker loss, tenant quotas and measured claim latency.
   [PostgreSQL row locking](https://www.postgresql.org/docs/current/explicit-locking.html)
   supplies relevant primitives; distributed correctness still needs application tests.
   source_event_date: undated current documentation, accessed 2026-10-16;
   confidence: medium; relevance: present single-host limit;
   direction_alignment: scalability; opportunity_or_risk: distributed leases and migrations;
   engineering_cost: high; disposition: monitor; roadmap_delta: none;
   verification_needed: failover, duplicate-claim rejection and migration rollback.
5. **Statistical decision calibration.** Target **1,000 null and shifted trials**,
   measured false-positive/power rates, missing pairs and degenerate inputs, with a
   published interpretation guide. [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
   describes paired resampling and degeneracy; it does not validate SimWeave's algorithm.
   source_event_date: undated current documentation, accessed 2026-10-16;
   confidence: high; relevance: inconclusive results need trustworthy interpretation;
   direction_alignment: reliable experiment decisions;
   opportunity_or_risk: overconfidence from small samples; engineering_cost: medium;
   disposition: monitor; roadmap_delta: none;
   verification_needed: deterministic calibration data and independent numeric checks.

Overall recommendation: prioritize 1 and 2 for the next milestone, using the
current browser and measured recovery cost as the foundation. Evidence gaps:
no multi-host, real-provider or statistical-calibration results are claimed.
