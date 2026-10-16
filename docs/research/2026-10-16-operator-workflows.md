# DirectionBriefV1: operator workflows

- schema_version: 1
- baseline_commit: 48474cba23b636d251f036597a0e5d8c1bdb8151
- scanned_at: 2026-10-16
- coverage: focused browser accessibility, SQLite consistency and recovery,
  identity integration and future multi-host scheduling.

1. finding: native controls and persistent, non-disruptive status suit the review
   workspace. [W3C alert pattern](https://www.w3.org/WAI/ARIA/apg/patterns/alert/).
   source_event_date: undated living documentation, accessed 2026-10-16.
   confidence: high; relevance: browser operation; direction_alignment: ease of use;
   opportunity_or_risk: asynchronous updates must not steal focus;
   engineering_cost: medium; disposition: adopt; roadmap_delta: approved SW012;
   verification_needed: 30 cases across two tenants and keyboard navigation.
2. finding: SQLite online backup provides a database snapshot, but cross-database
   and object consistency still requires an application boundary.
   [SQLite backup](https://www.sqlite.org/backup.html).
   source_event_date: undated documentation, accessed 2026-10-16.
   confidence: high; relevance: maintenance; direction_alignment: portability;
   opportunity_or_risk: in-flight writes and interruption;
   engineering_cost: medium; disposition: adopt; roadmap_delta: approved SW012;
   verification_needed: four workers, 10 GiB recovery and three interruption points.
3. finding: PostgreSQL row locks support a future claim design; Keycloak provides
   OIDC integration endpoints. Neither alone proves a production deployment.
   [PostgreSQL locking](https://www.postgresql.org/docs/current/explicit-locking.html),
   [Keycloak OIDC](https://www.keycloak.org/securing-apps/oidc-layers).
   source_event_date: undated living documentation, accessed 2026-10-16.
   confidence: high; relevance: future interoperability; direction_alignment: SaaS;
   opportunity_or_risk: migration and real-provider behavior;
   engineering_cost: high; disposition: monitor; roadmap_delta: none;
   verification_needed: separately approved real multi-host/provider drills.

Overall recommendation: deliver the two accepted operator workflows, preserving
single-host and explicit-approval boundaries. Evidence gaps: browsing cannot prove
runtime durability, browser behavior, power-loss safety or deployment suitability.
