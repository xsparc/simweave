# ADR 0001: Portable contracts and a modular control plane

Status: accepted

Date: 2026-10-13

## Context

The first MVP must run on a laptop, integrate with SaaS systems, and accommodate
more simulators without binding experiment definitions to one vendor.

## Decision

Use Python 3.11+ and Pydantic for closed, versioned scenario contracts; implement
an independent streaming engine and explicit adapter protocol. Use FastAPI for
HTTP/OpenAPI, a separate durable worker, and SQLite WAL for single-host operation.
Build a small browser dashboard without a frontend framework or build chain.

Start with a reference cart and optional headless MuJoCo. Provide an honest,
capability-checked ROS 2 lifecycle bridge; do not claim arbitrary robot execution
from generic reset/step interfaces. Only generated built-in MuJoCo models are
accepted. Do not accept arbitrary XML, asset URLs, controller code, or shell input.

## Consequences

One install and one contract serve CLI, UI, and API users. CPU simulation is kept
off the API event loop. SQLite trades easy operations for a single-host boundary.
PostgreSQL, object storage, OIDC, and sandboxed remote workers remain explicit
replacement points. Telemetry and scenario digests make comparisons auditable,
but do not promise cross-platform bitwise determinism or authenticate artifacts.

## Evidence

The initial request authorizes this MVP architecture. Current primary-source
research is recorded in `docs/research/2026-10-13-direction.md`; implemented
behavior and tests take precedence over predictions about future scalability.
