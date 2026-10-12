# Design history

2026-10-13: established a standalone SimWeave repository and MIT license. Scoped
the first delivery to three stacked PRs with contracts/core, execution/API, then
dashboard/operations. ADR 0001 records the architectural tradeoffs. The roadmap
records acceptance criteria and deferred capabilities.

The evidence registry is a derived navigation and verification index. It does
not grant new authority. Preserve the distinction between local tests, CI results,
real simulator execution, and contract tests using fake transports.
