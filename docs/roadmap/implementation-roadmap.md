# Implementation roadmap

## SW017: retained-artifact integrity audit

After SW016's merge, delegated research/scope selection prioritizes detecting
damaged retained evidence before recovery. ADR 0015 defines bounded, resumable,
tenant-scoped operator audits and read-only failure reporting.

## SW016: incremental checkpoints

After SW015's merge, delegated research/scope selection selects the remaining
incremental-recovery recommendation. ADR 0014 adds verified object reuse, restart
from complete cached objects and measured 10 GiB/1% churn acceptance.

## SW015: statistical calibration

The 2026-10-19 request continues delegated research/scope selection and draft
delivery. ADR 0013 selects the existing statistical calibration recommendation:
1,000 seeded trials per null/boundary/shifted/skewed cohort, observed rates and
coverage, edge-case verification and an interpretation guide.

## SW014: guided baseline review

The 2026-10-18 request delegates research, scope selection, delivery and a draft PR.
After SW013's merge, ADR 0012 selects explicit browser promotion/rollback, recorded
decision summaries and paginated history. Acceptance includes 20 two-tenant browser
cases, a 30-pair fixture and generation-conflict handling. No merge is authorized.

The initial request authorizes exactly three MVP delivery slices. The initial
MIT license/bootstrap commit is outside the feature slices. PRs form a stack and
remain reviewable before a maintainer merges them in order.

| Slice | Scope | Acceptance |
| --- | --- | --- |
| SW001 | Contracts, deterministic reference engine, CLI, replay, architecture | Invalid scenarios fail; equal seeds reproduce; corruption is detected; CLI round trip passes |
| SW002 | MuJoCo, ROS lifecycle bridge, durable worker, tenant-scoped API | Real MuJoCo repeats; queue claims and cancellation are safe; API isolation, quotas, and replay tests pass; ROS transport contract tests pass |
| SW003 | Dashboard, container, CI, integration docs, operations | Browser launch/run/replay works; portable packaging and full suite pass; actual environment gaps are recorded |

## Approved next slice: SW004

The maintainer approved development and verification of a complete ROS/Gazebo
cart experiment, followed by a draft PR. Implement ADR 0002: isolated native
fixture, standard ROS lifecycle, acknowledged forces, real joint observations,
existing telemetry/gates/replay, and live MuJoCo comparison. Acceptance is defined
in that ADR and `docs/governance/ros-gazebo-validation.md`. Additional milestone
recommendations remain advisory until accepted.

## Approved next slice: SW005

The maintainer approved regression suites/CI gates and the comparison dashboard,
followed by verification and a draft PR. ADR 0003 defines the bounded matrix,
portable reports, same-input comparison rules, and browser acceptance. Deliver
both as one regression workflow, with sequential local execution and read-only
dashboard review. Future recommendations remain advisory.

## Approved next slice: SW006

After PR10 was squash-merged, the maintainer approved reproducible failure bundles
and offline reports/onboarding. ADR 0004 defines portable checked recordings,
explicit retained-image reruns, self-contained review/export, CI artifacts, and
three observed workflow checks. Record browser/file-dialog limitations separately
from functional verification. Later milestone recommendations remain advisory.

## Approved next slice: SW007

After PR11 was squash-merged, the maintainer approved statistical regression
summaries and immutable baseline history/promotion, verification and a draft PR.
ADR 0005 defines 30 paired seeds per adapter, reproducible practical-threshold
decisions, explicit approval/rollback events and 20 candidate comparisons against
one pinned baseline. This slice adds a local decision workflow, not hosted baseline
management or automatic promotion. Future milestone recommendations remain advisory.

## Approved next slice: SW008

After PR12 was squash-merged, the maintainer approved portable catalog archives
and a tenant-scoped baseline API, verification and a draft PR. ADR 0006 defines
100-build cross-platform recovery, digest preservation, corrupt-input rejection,
two-tenant reader/importer/approver isolation and an example client. Future milestone
recommendations remain advisory; no merge or deployment is authorized.

## Approved next slice: SW009

After PR13's squash merge, the maintainer approved OIDC-backed identity and signed
evidence provenance, verification and a draft PR. ADR 0007 defines catalog access
tokens with two-tenant role/scope isolation and key rotation, plus policy-pinned
GitHub attestation verification and snapshot-safe recovery. Synthetic CI signing
is verification, not release or deployment. Future recommendations remain advisory.

## Later review triggers

SW011 is approved after PR15's squash merge: connect retained artifacts to catalog
review and add operational metrics/coordinated recovery. ADR 0009 targets 100
authenticated job-to-comparison flows and verified recovery of 1,000 bundles and
100 jobs within five minutes on the bounded reference fixture. Verification and
a draft PR are authorized. Subsequent recommendations remain advisory.

SW010 is approved after PR14's squash merge: durable filesystem/S3 bundle storage
and worker-scheduled suites. ADR 0008 targets 1,000 retained/recovered bundles and
100 jobs across four local workers/two tenants, including cancellation and explicit
recovery from worker loss. Verification and a draft PR are authorized; subsequent
milestone recommendations remain advisory.

- Additional ROS/Gazebo robot fixtures beyond the built-in cart: a named model,
  actuator mapping, sensor contract, and real integration environment are agreed.
- PostgreSQL and multi-host workers: single-host throughput/storage measurements or
  a concrete multi-host deployment requirement justify migration.
- Organizations and login UX: first internet-facing deployment; the OIDC resource
  server is not a complete identity product or provider provisioning workflow.
- Isaac Sim, Webots, more robot types: an explicit scenario and adapter conformance
  suite for the requested environment are available.

Ongoing stewardship reviews bugs, dependencies, compatibility, and this evidence
weekly. It may prepare bounded draft maintenance PRs; consequential product scope,
merges, paid execution, releases, and deployments require maintainer decisions.


## Approved next slice: SW012

After PR16's squash merge, the maintainer approved browser suite review and
maintenance/recovery automation. ADR 0010 targets 30 browser cases across two
tenants, four-worker drain, 10 GiB recovery, three interruption points and measured
recovery time. Verification and a draft PR are authorized. Next recommendations
remain advisory and do not authorize implementation or deployment.

## SW013: provider and distributed suite boundary

After PR17's squash merge, recommendations #3 and #4 are approved for development,
verification and a draft PR. ADR 0011 defines real Keycloak role/rotation/expiry
checks and PostgreSQL suite scheduling with 1,000 jobs and eight workers across
two isolated container hosts. The fixture has one physical host. SQLite remains
the default and the catalog retains one API authority. Subsequent milestone
recommendations remain advisory; no merge, deployment or release is authorized.

## SW018: deterministic scenario sweeps

After SW017's merge, delegated scope selection selects bounded experiment authoring.
ADR 0016 defines a plan-only parameter grid with strict axes, deterministic output,
full Suite admission and reference/MuJoCo validation. No automatic tuning or
promotion is included. See operations/scenario-sweeps.md.

## SW019: parameter-linked sweep result review

After SW018's merge, the 2026-10-22 request continues delegated scope selection.
ADR 0017 adds bounded descriptive results tied to the exact Sweep plan, with
visible execution failures and preserved comparison warnings. Optimization,
statistical inference and promotion remain separate workflows.

## SW020: Offline HTML sweep reports

The delegated 2026-10-23 scope continues the merged evidence milestone.
Decision: `docs/architecture/decisions/0018-offline-sweep-report.md`.
Acceptance: Escaped hostile titles produce no executable tags or event attributes; CSP matches fixed CSS; metric values and evidence hashes match validated summaries; incomplete points withhold metrics; CLI validates before writing and refuses overwrite.

## SW021: CSV sweep export

The delegated 2026-10-25 scope closes a bounded workflow gap on current main.
Decision: `docs/architecture/decisions/0019-sweep-csv-export.md`.
Acceptance: Deterministic CSV parses to the expected row count and columns; numeric round trips, source hashes and seed ordering match the review; hostile labels remain text-prefixed; incomplete metrics are blank; CLI preserves CRLF and refuses overwrite or invalid evidence.
