# ADR 0002: Isolated ROS/Gazebo cart experiments

Status: accepted

Date: 2026-10-13

## Context and approved scope

SW004 implements the approved complete ROS/Gazebo cart experiment. The existing
ROS lifecycle bridge cannot supply robot-specific forces or sensor observations.
Publishing a force and immediately stepping another asynchronous process does
not establish that the intended force reached the physics update.

## Decision

Add `gazebo` to the v1 adapter identifiers without changing existing defaults or
recording semantics. A fixed, installed ROS package launches one headless Gazebo
Harmonic server per experiment, using a unique ROS namespace and Gazebo partition.
The native fixture generates only the built-in, contact-free prismatic cart from
bounded numeric parameters. Scenario data cannot select executables, XML, plugins,
paths, namespaces, or remote assets. Python imports ROS lazily.

Use standard `simulation_interfaces` feature discovery, full reset, pause, and
finite stepping. Three typed fixture services configure the cart, acknowledge a
force for an expected step, and read the completed joint state. A single ROS
executor serializes these operations. Gazebo's physics system advances the joint;
the Python engine retains PD control, seeded sensor noise, disturbances, metrics,
gates, and recording integrity. Validate the native step index and simulation time
before accepting a sample. A timeout has an unknown outcome and aborts the run;
mutations are never automatically retried.

Select the DART physics plugin explicitly and fix the native fixture seed to zero;
all scenario-controlled randomization is the engine's seeded position noise.
Require whole-nanosecond timesteps so native and scenario clocks cannot drift.

Reset reconstructs the world. Partial reset scopes and free-running simulation
are unsupported and rejected. Feature discovery does not advertise partial scopes.
The existing generic lifecycle CLI remains available for external simulators.

The API and worker must share the same operator-installed runtime. Capability
discovery checks installation, not fleet readiness. Each run owns and reaps its
child; the service does not attach to an operator's existing simulation world.

## Non-scope and risks

No arbitrary robots, contact models, user plugins, GPU rendering, remote ROS
clusters, new simulator vendors, or hosted identity system. The cart fixture is
not a general Gazebo adapter. ROS/DDS is a trusted local transport; process
separation is not an OS security sandbox. Container verification uses no external
network and an unprivileged user. Operators should isolate workers similarly.

Per-step ROS round trips favor explicit ordering over throughput. Process startup
and package size are additional costs. Older clients that hardcode the v1 adapter
enum need regeneration to submit Gazebo scenarios; existing scenarios still work.
Different physics engines can yield different trajectories. Numerical tolerances
are specific to the tested cart, never a cross-engine determinism promise.

## Acceptance and verification

- Live ROS services execute Gazebo physics, including nonzero initial state,
  force response, disturbance recovery, metrics, and pass/fail gates.
- Same-environment repeated seeded runs reproduce telemetry; resets and separate
  instances do not interfere.
- MuJoCo and Gazebo satisfy shared gates for the fixture; comparison tolerances
  are declared in the live tests.
- Reject invalid values, stale force commands, unsupported lifecycle requests,
  and excess work. Detect backend exit, timeouts, and invalid observations.
- CLI and tenant-scoped API recordings remain verifiable offline.
- Portable tests run without ROS. A required container CI job runs real ROS/Gazebo
  integration tests without silently skipping missing dependencies.

See `docs/research/2026-10-13-ros-gazebo.md` and the SW004 validation record.
