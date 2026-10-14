# Implementation roadmap

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

## Later review triggers

- Additional ROS/Gazebo robot fixtures beyond the built-in cart: a named model,
  actuator mapping, sensor contract, and real integration environment are agreed.
- PostgreSQL and object storage: single-host throughput/storage measurements or
  a concrete multi-host deployment requirement justify migration.
- OIDC and organizations: first internet-facing deployment; token mapping is an
  MVP integration mechanism, not a complete identity product.
- Isaac Sim, Webots, more robot types: an explicit scenario and adapter conformance
  suite for the requested environment are available.

Ongoing stewardship reviews bugs, dependencies, compatibility, and this evidence
weekly. It may prepare bounded draft maintenance PRs; consequential product scope,
merges, paid execution, releases, and deployments require maintainer decisions.
