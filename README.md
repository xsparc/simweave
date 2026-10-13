# SimWeave

Vendor-neutral simulation experiments for robotics and physical AI.

Define a world, robot, controller, sensor noise, disturbances, seed, and quality
gates in one JSON scenario. Run it headlessly, inspect telemetry, and verify the
recording. The first experiment is a one-dimensional cart recovering from a force
disturbance.

![SimWeave experiment dashboard](docs/assets/dashboard.jpg)

## Try the dashboard

```sh
git clone https://github.com/xsparc/simweave.git
cd simweave
python -m venv .venv
# Activate .venv (PowerShell: .venv\Scripts\Activate.ps1; POSIX: . .venv/bin/activate).
python -m pip install -e '.[mujoco]'
simweave demo
```

Open the local URL printed by the command. The demo starts the API and an
independent worker, creates a temporary session token, and connects the dashboard.
The token is carried in the URL fragment, removed from browser history on load,
and held only in tab memory. Avoid sharing that URL while the server is running.
Use Ctrl+C to stop. Runs persist in `.simweave/demo.sqlite3`; the token changes
at the next start. `simweave demo --port 8001` uses another local port.

Choose Reference or MuJoCo, edit the scenario or its full JSON contract, and run
the experiment. Select a run to inspect quality gates, play/scrub its trajectory,
verify integrity, or export a recording. No frontend build or cloud account is
required. The API, CLI, and dashboard share the same scenario contract.

The demo binds only to loopback. For persistent authentication and separately
supervised processes, follow the [service guide](docs/operations/api.md).

## Local CLI

```sh
python -m venv .venv
# Activate .venv using your shell's activation command.
python -m pip install -e '.[dev]'
simweave validate examples/cart-recovery.json
simweave run examples/cart-recovery.json --output .simweave/example
simweave replay .simweave/example
```

Output contains `scenario.json`, `result.json`, and streaming `telemetry.jsonl`.
Exit codes: 0 = gates pass, 1 = completed with failed gates, 2 = input/runtime error.
Existing output directories are never overwritten. `simweave init scenario.json`
creates a default scenario; `simweave schema` prints its JSON Schema.

The reference simulator is a small deterministic test/demo model. Repeatability
requires the same engine, adapter, dependency versions, platform, and seed;
different simulators are not expected to be numerically identical.

## Service and simulator integrations

Install `.[dev,mujoco]` for the optional physics engine. Change the scenario's
`adapter` to `mujoco` and use the same CLI. No GPU or viewer is required.

The authenticated HTTP service and durable worker run independently:
`simweave serve` and `simweave worker`. Configure the token-to-tenant mapping first
as described in the [API quickstart](docs/operations/api.md). OpenAPI lives at
`/docs`; tenant-scoped run endpoints support idempotency, cancellation, paginated
telemetry, gate verification, and portable recording export.

The [ROS/Gazebo integration](docs/operations/ros2.md) runs the built-in cart through
real headless Gazebo physics, with acknowledged forces, joint observations,
standard ROS lifecycle services, and the same metrics/gates/replay. Use
`adapter: "gazebo"` in a ROS-enabled installation. An isolated verification image
and live conformance suite are included; no host ROS install or GPU is needed
when using that image. The generic lifecycle CLI remains available for existing
external simulators. Arbitrary robot models remain outside this adapter's scope.

For a SaaS or CI integration, set `SIMWEAVE_URL` and `SIMWEAVE_TOKEN` and run
`python examples/submit.py examples/cart-recovery.json`. The standard-library
client submits a scenario, waits for completion, and exits according to its gates.

## Container

Set `SIMWEAVE_TOKENS` as described in the service guide, then:

```sh
docker compose up --build
```

The API is exposed on loopback port 8000. The worker shares a named local data
volume. Both run as an unprivileged user; no privileged mode or host Docker socket
is required. `docker compose down` stops the service and retains recordings.
See [operations](docs/operations/api.md) for backup, retention, and scaling limits.

## Engineering

```sh
python -m pytest
ruff check .
ruff format --check .
python scripts/check_governance.py --strict
```

See [architecture](docs/architecture/overview.md), [implementation roadmap](docs/roadmap/implementation-roadmap.md),
[security boundary](docs/security/threat-model.md), and [validation](docs/governance/verification-and-validation.md).
`uv.lock` records the resolved environment; use `uv sync --frozen --extra dev`
for a locked development install.

Benchmark the streaming core with `python scripts/benchmark.py --adapter reference`
or `--adapter mujoco`. See the [validation report](docs/governance/mvp-validation.md)
for measured results and remaining integration gaps. Container runtime dependencies
are pinned with hashes in `requirements.lock`, generated from `uv.lock`.

## Stewardship

The project follows an OpenSteward research, delivery, and evidence workflow.
The [stewardship policy](docs/governance/stewardship.md) describes ongoing work and
review boundaries. New delivery PRs target `main`. When a dependency is
squash-merged, restack dependent changes and retarget before deleting its branch.

Licensed under the MIT License.
