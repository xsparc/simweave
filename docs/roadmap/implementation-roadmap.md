# Implementation roadmap

The initial request authorizes exactly three MVP delivery slices. The initial
MIT license/bootstrap commit is outside the feature slices. PRs form a stack and
remain reviewable before a maintainer merges them in order.

| Slice | Scope | Acceptance |
| --- | --- | --- |
| SW001 | Contracts, deterministic reference engine, CLI, replay, architecture | Invalid scenarios fail; equal seeds reproduce; corruption is detected; CLI round trip passes |
| SW002 | MuJoCo, ROS lifecycle bridge, durable worker, tenant-scoped API | Real MuJoCo repeats; queue claims and cancellation are safe; API isolation, quotas, and replay tests pass; ROS transport contract tests pass |
| SW003 | Dashboard, container, CI, integration docs, operations | Browser launch/run/replay works; portable packaging and full suite pass; actual environment gaps are recorded |

## Next review triggers

- Full ROS/Gazebo experiment adapter: a named robot model, actuator mapping,
  sensor contract, and real integration environment become available.
- PostgreSQL and object storage: single-host throughput/storage measurements or
  a concrete multi-host deployment requirement justify migration.
- OIDC and organizations: first internet-facing deployment; token mapping is an
  MVP integration mechanism, not a complete identity product.
- Isaac Sim, Webots, more robot types: an explicit scenario and adapter conformance
  suite for the requested environment are available.

Ongoing stewardship reviews bugs, dependencies, compatibility, and this evidence
weekly. It may prepare bounded draft maintenance PRs; consequential product scope,
merges, paid execution, releases, and deployments require maintainer decisions.
