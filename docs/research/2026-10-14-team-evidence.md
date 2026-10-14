# Accepted research: team-ready regression evidence

DirectionBriefV1, schema_version: 1. baseline_commit:
`401c0f3cc8fd97530aa503601e0c7cc1fcb11533`. scanned_at: 2026-10-14.
Coverage: portable persistence, transaction consistency, object and function
authorization, bounded uploads. The maintainer accepted recommendations 1 and 2.

1. **Portable catalog recovery — adopt.**
   [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) and
   [transactions](https://www.sqlite.org/lang_transaction.html) support stable read
   snapshots and atomic writes. Source event date: live documentation checked on
   scan date; transaction page updated 2026-02-18. Confidence: high in transactions,
   medium in filesystem portability until tested. Relevance/alignment: portable,
   auditable evidence. Opportunity: preserve history independently of SQLite files.
   Risks: partial exports and corruption. Cost: medium. Roadmap delta: SW008 archive
   and fresh restore. Verify 100 builds Windows-to-Linux and back, unchanged approval
   and comparison digests, failure atomicity and bounded parsing.

2. **Tenant and role boundaries — adopt.**
   [OWASP object authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)
   (2023 edition, checked on scan date) requires authorization for accessed objects.
   [FastAPI permission guidance](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)
   (undated live docs, checked on scan date) makes enforcement an application
   responsibility. Confidence: high. Relevance/alignment: SaaS interoperability
   without trusting client tenant or approval labels. Opportunity: shared baseline
   workflows. Risks: confused permissions, forged identity, resource exhaustion.
   Cost: high. Roadmap delta: SW008 reader/importer/approver credentials,
   server-selected catalogs, bounded uploads and example client. Verify two tenants
   across routes and roles, spoofing, concurrent approval and restart.

Overall recommendation: implement both accepted capabilities behind versioned
contracts; keep restoration an operator action. Evidence gaps: Internet deployment,
OIDC, tamper-proof audit, signed archives, network filesystems, multi-host concurrency
and sustained multi-user load. None is claimed by SW008.
