# Next milestone: Operator-ready experiment workflows

DirectionBriefV1; schema_version: 1; scanned_at: 2026-10-15;
baseline_commit: 01a4586910d22181e8065fe633b2c2998ee90382, plus the SW011 draft.
Coverage: connected review usability, maintenance/recovery, distributed scheduling,
identity interoperability and statistical validity. All five directions are advisory;
they do not authorize implementation or change requirements.

| Priority / finding | Proposed target | Source event date / evidence / confidence / alignment | Cost, risk and disposition |
| --- | --- | --- | --- |
| 1. Put the complete review flow in the browser | Submit, inspect, cancel, download, import and compare suites in one workspace; verify 30 workflow cases across two tenants with keyboard-accessible controls | SW011 exposes APIs/CLI; [W3C interaction patterns](https://www.w3.org/WAI/ARIA/apg/patterns/), living guidance checked 2026-10-15. High confidence; closes the remaining usability gap | Medium; preserve role boundaries and distinguish inconclusive decisions. Adopt next, subject to approval |
| 2. Automate safe maintenance and recovery | Drain four workers, pause admission, checkpoint and resume; recover a 10 GiB fixture with no lost references across three injected interruption points, publishing measured recovery time | Current checkpoint requires manually stopped writers; [SQLite backup](https://www.sqlite.org/backup.html), checked 2026-10-15. High confidence; makes operational safety observable and repeatable | Medium/high; crash-safe maintenance state and disk headroom. Adopt next, subject to approval |
| 3. Add multi-host scheduling | Optional PostgreSQL queue: 1,000 jobs, eight workers, two hosts, with stale completion rejection during network failure | [PostgreSQL locking](https://www.postgresql.org/docs/current/sql-select.html), checked 2026-10-15. Medium confidence in demand, high architectural fit | High; migration and distributed failure complexity. Monitor until multi-host demand |
| 4. Verify real-provider onboarding | Reproducible Keycloak setup for two tenants/three catalog roles; expiry, rotation and revocation checks without weakening access-token validation | [Keycloak OIDC](https://www.keycloak.org/securing-apps/oidc-layers), checked 2026-10-15. Medium confidence; improves SaaS interoperability | Medium; claim/algorithm/profile differences. Monitor pending deployment intent |
| 5. Calibrate statistical decisions | 1,000 known-null/known-shift trials with published interval coverage, false-positive rate and power across sample counts | [SciPy bootstrap reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html), checked 2026-10-15. High confidence in need; strengthens scientific meaning | Medium; representative populations and acceptance bands must be agreed. Monitor |

Overall recommendation: priorities 1 and 2 make the newly connected backend useful
to operators before adding distributed infrastructure. Roadmap delta: none until
maintainer acceptance. Verification needed: the targets above are proposed, not
measured. Evidence gaps include browser task completion, large-object recovery,
multi-host behavior, live identity-provider profiles and empirical calibration.
