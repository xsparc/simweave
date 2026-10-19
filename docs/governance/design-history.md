# Design history

2026-10-19, SW015: the next-milestone request continues delegated scope selection.
ADR 0013 selects the earlier statistical calibration recommendation. The existing
classifier now has a bounded offline experiment with explicit observed rates,
coverage and interpretation limits. See calibration-validation.md.

2026-10-18, SW014: delegated next-scope research selects guided baseline review.
ADR 0012 reuses existing catalog role and generation contracts, adds explicit
browser confirmation and readable recorded decisions, and preserves immutable
approval history. See guided-review-validation.md for executed checks and limits.

2026-10-13: established a standalone SimWeave repository and MIT license. Scoped
the first delivery to three stacked PRs with contracts/core, execution/API, then
dashboard/operations. ADR 0001 records the architectural tradeoffs. The roadmap
records acceptance criteria and deferred capabilities.

The evidence registry is a derived navigation and verification index. It does
not grant new authority. Preserve the distinction between local tests, CI results,
real simulator execution, and contract tests using fake transports.

SW001 established contracts, the reference engine, and offline replay. SW002
added real MuJoCo, ROS lifecycle control, and the authenticated durable service.
SW003 added the dashboard, one-command demo, frozen dependency exports,
container operations, cross-platform CI, package checks, and stewardship policy.
The MVP's actual validation scope and gaps are recorded in `mvp-validation.md`.

SW004: the maintainer approved the ROS/Gazebo cart integration and draft delivery.
ADR 0002 records dedicated worlds, standard lifecycle services, acknowledged
forces, native joint observations, and explicit clock verification. Live testing
exposed the private-context/global-executor mismatch in the generic ROS bridge;
both transports now own matching executors. Verification distinguishes seeded
repeatability from tolerance-based cross-engine agreement. The delivery includes
PR3's existing changes as a separate prerequisite because its squash merge did
not target main. New work targets main directly.

SW005: after PR4 was squash-merged to main, the maintainer approved regression
suites and the comparison dashboard. ADR 0003 keeps bounded local execution and
pure comparison logic separate from the service. JSON/JUnit reports retain full
recordings while the browser uses bounded previews. Native positive/negative
matrices, API isolation, report validation, and the browser inspection/export
workflow were exercised. The two-minute usability target remains a documented
follow-up because file-dialog automation delayed the timed check; see the
regression validation record.

2026-10-14, SW006: after PR10's squash merge, the maintainer approved reproducible
failure bundles and offline reports. ADR 0004 separates data validation, local
runtime capture, offline rendering, and explicitly selected container execution.
Fresh-container checks reproduced all six reference/MuJoCo/Gazebo recordings and
their intended gate failures. Full telemetry/previews, bounded ZIP input, hostile
HTML text, and export content were verified. Direct file-open and the two-minute
end-to-end save target remain documented browser-tool limitations; the evidence
index retains in-progress status rather than declaring those criteria verified.

2026-10-14, SW007: the maintainer approved statistical regression summaries and
baseline history after PR11's squash merge. ADR 0005 preserves existing suite
contracts and adds a pure bounded paired analysis with explicit practical
tolerances. A separate local catalog imports verified evidence and records
immutable builds, policies, approval generations and rollback events. Cross-build
decisions pin approved evidence rather than the candidate suite's internal
baseline. Actual checks and limits are recorded in `decisions-validation.md`.

2026-10-14, SW008: the maintainer approved portable catalog archives and tenant
baseline permissions after PR12's squash merge. ADR 0006 adds data-only bounded
recovery with atomic fresh publication, and server-selected catalogs with separate
reader/importer/approver roles. Existing run credentials gain no catalog access.
Verification is recorded in `team-evidence-validation.md`.

2026-10-14, SW009: after PR13's squash merge, the maintainer approved OIDC-backed
catalog identity and signed evidence provenance. ADR 0007 defines a pinned access
token profile, server-bound subjects and role scopes, bounded JWKS refresh, and
policy-constrained GitHub attestation verification. Restore consumes the exact
verified snapshot. Synthetic CI signing tests provenance without publishing a
release. Evidence is recorded in `trusted-evidence-validation.md`.
