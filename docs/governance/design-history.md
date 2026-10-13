# Design history

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
