# ADR 0012: Guided baseline review

Status: accepted under delegated milestone selection, 2026-10-18.

Baseline: `622c2c1`. The user requested the next milestone and draft PR, then
delegated research and scope selection. SW014 completes the existing workspace's
review workflow using the catalog API and its reader/importer/approver separation.

Approvers explicitly review a selected build, policy, reason and expected catalog
generation in a native modal dialog. Cancel receives initial focus; Escape cancels.
Confirmation sends the captured request once. A rejected or uncertain write
invalidates the cached generation and requires refreshed evidence and confirmation.
Rollback displays and restores a selected earlier approval's exact build and policy.
The server remains the authority for identity, tenant, generation and validation.

Readers and approvers can inspect recorded comparisons and paginated immutable
approval history. Tables show paired counts, metric changes, confidence intervals,
tolerances, verdicts and warnings. Inconclusive never means pass. Credentials stay
in memory; disconnect clears pending approvals and displayed evidence.

Acceptance: 20 real browser/API cases across two tenants, 30 paired seeds, separate
write permissions, cross-tenant denial, keyboard cancellation/confirmation,
concurrent-generation rejection, rollback policy/identity preservation, readable
summaries, history and disconnect clearing. Run existing workspace checks, full
pytest, lint, formatting, syntax and static/strict governance checks.

Expected paths: static workspace, browser acceptance/CI, operations and governance.
Risks: accidental promotion, stale generations, late responses and misleading
statistical interpretation. No automatic promotion, new permissions, login UX,
statistical algorithm change, simulator or distributed recovery change.

Research: `docs/research/2026-10-18-guided-review.md`.
