# DirectionBriefV1: SimWeave MVP

- schema_version: 1
- baseline_commit: c6abbd0 (MIT/bootstrap)
- scanned_at: 2026-10-13 (Australia/Sydney)
- coverage: simulator interfaces, Python simulation, HTTP deployment, input
  validation, persistence constraints, and local governance compatibility.

| Finding and primary source | Event date | Confidence / relevance | Alignment; opportunity or risk | Cost | Disposition / roadmap delta / verification |
| --- | --- | --- | --- | --- | --- |
| ROS provides feature discovery, reset scopes, and finite stepping in [simulation_interfaces](https://github.com/ros-simulation/simulation_interfaces) | Undated current interface; observed 2026-10-13 | High / high | Supports neutral lifecycle control; no standard cart actuator or seed guarantee | Medium | Adopt a bounded lifecycle bridge in SW002; real ROS integration remains required |
| [MuJoCo Python bindings](https://mujoco.readthedocs.io/en/stable/python.html) expose engine state and stepping without requiring a viewer | Undated current docs; observed 2026-10-13 | High / high | A practical optional headless physics adapter; copy state values for telemetry | Low | Adopt SW002; test real wheel and repeatability locally and in CI |
| [FastAPI processes](https://fastapi.tiangolo.com/deployment/server-workers/) replicate service execution, not durable simulation scheduling | Undated current docs; observed 2026-10-13 | High / high | Separate API and execution to avoid CPU-bound request handling | Medium | Adopt SW002 durable worker; test claims and failure recovery |
| [SQLite WAL](https://www.sqlite.org/wal.html) requires shared-memory coordination on one host | Undated current docs; observed 2026-10-13 | High / high | Easy portable MVP; multi-host writes need a different store | Low now, medium migration | Adopt single-host scope; measure before migration |
| [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/) rejects unwanted coercion | Undated current docs; observed 2026-10-13 | High / high | Closed inputs reduce ambiguous experiment definitions | Low | Adopt SW001; test malformed and non-finite input |

Overall recommendation: implement the three authorized slices with explicit
capability and deployment limits. Defer distributed scheduling and arbitrary
robot plugins until representative integration requirements exist.

Evidence gaps: no AeroLoop source or lessons were provided; no AeroLoop-specific
claims are made. No live ROS/Gazebo environment has been exercised. The installed
OpenSteward governance checker hardcodes its own repository identity; SimWeave
uses a repository-local checker of its own evidence instead of falsifying that
identity. Research is advisory; the initial architecture is a delivery decision
within the requested MVP scope, not a blanket authorization for later expansion.
