# DirectionBriefV1: provider and distributed queue

- schema_version: 1
- baseline_commit: 505b6195c2f2f654e1c7e014ad95b1f7ad6d9ba5
- scanned_at: 2026-10-17
- coverage: focused provider interoperability, PostgreSQL concurrency and bounded
  connection management for the two accepted recommendations.

1. finding: Keycloak exposes token, logout, revocation and introspection endpoints.
   [Keycloak OIDC](https://www.keycloak.org/securing-apps/oidc-layers).
   source_event_date: undated living documentation, accessed 2026-10-17.
   confidence: high; relevance: real provider integration; direction_alignment: SaaS;
   opportunity_or_risk: provider invalidation does not imply offline JWT revocation;
   engineering_cost: medium; disposition: adopt; roadmap_delta: approved SW013;
   verification_needed: two tenants, three roles, rotation, expiry and invalidation.
2. finding: PostgreSQL explicitly supports SKIP LOCKED for queue-like consumers.
   [SELECT reference](https://www.postgresql.org/docs/current/sql-select.html).
   source_event_date: undated living documentation, accessed 2026-10-17.
   confidence: high; relevance: multi-worker claims; direction_alignment: scalability;
   opportunity_or_risk: row locks alone do not fence stale completion or enforce quotas;
   engineering_cost: high; disposition: adopt; roadmap_delta: approved SW013;
   verification_needed: 1,000 jobs, eight workers, loss, quotas and tenant isolation.
3. finding: bounded pools provide connection lifecycle and timeout controls.
   [Psycopg pool](https://www.psycopg.org/psycopg3/docs/advanced/pool.html).
   source_event_date: undated living documentation, accessed 2026-10-17.
   confidence: high; relevance: shared database lifecycle; direction_alignment: performance;
   opportunity_or_risk: nested gate transactions can exhaust a shared pool;
   engineering_cost: medium; disposition: adopt; roadmap_delta: approved SW013;
   verification_needed: independent admission pool, concurrency and restart tests.

Overall recommendation: implement the accepted provider and suite backend boundary,
retain SQLite defaults and one catalog authority. Evidence gaps: two physical
hosts, PostgreSQL HA and coordinated recovery, browser login and immediate token
revocation remain unverified and are not implied by local container measurements.
