# SW004 ROS/Gazebo validation

Status: locally verified, 2026-10-13. GitHub CI results are reported on the PR.

The live suite under `integrations/ros2/tests/` requires real ROS 2 Jazzy,
Gazebo Harmonic, MuJoCo, and the compiled `simweave_gazebo` fixture. It contains
no fallback fake transport and no dependency skips. Portable protocol tests under
`tests/test_gazebo.py` exercise failures without importing ROS.

## Executed checks

- Portable suite: 69 tests passed on Python 3.12, including real MuJoCo.
- Live integration image: 15 tests passed in 134.10 seconds under a 2 CPU / 4 GiB
  limit, as a non-root user with external networking disabled. This is total test
  duration including process startup/cleanup, not a simulation throughput claim.
- Repeated 600-step trajectories for seeds 7, 42, and 99, with noisy position
  observations and a timed disturbance: exact within-environment telemetry/digest
  equality across repeats; both Gazebo and MuJoCo passed the shared final-error
  gate. RMSE differences were below 0.02 m and per-sample position differences
  below 0.03 m. These are tested tolerance budgets, not universal physics bounds.
- Nonzero position/velocity matched the analytical unforced trajectory at
  timesteps 0.001, 0.0037, 0.01, and 0.1 seconds. Independent worlds and repeated
  resets did not interfere.
- Native services rejected stale force indices, NaN force, excessive stepping,
  partial reset, and unsupported play. Portable tests checked early rejection of
  sub-nanosecond timesteps, missing capabilities, bad clocks, and uncertain calls.
- A stopped native process caused a bounded timeout and was killed/reaped.
  Killing the experiment owner terminated its native child.
- The generic lifecycle transport successfully discovered features, stepped,
  and reset using its private ROS context and matching executor.
- CLI execution/replay passed. The authenticated API submitted a real Gazebo job,
  the worker completed it, an intentionally failing quality gate remained visible,
  recording verification passed, and the exported JSONL replay returned gate-fail
  exit code 1. No physical rerun is claimed by recording replay.
- Ruff lint/format, JavaScript syntax, static and dated strict governance, and
  diff whitespace checks passed. Source and wheel builds passed; the wheel
  contains the Gazebo Python adapter and dashboard assets.

## Reproduce

```sh
python -m pytest
ruff check .
ruff format --check .
node --check src/simweave/static/app.js
python scripts/check_governance.py --as-of 2026-10-13 --strict
docker build -f integrations/ros2/Dockerfile -t simweave:ros-cart .
docker run --rm --network none --pids-limit 256 --memory 4g --cpus 2 \
  simweave:ros-cart python -m pytest integrations/ros2/tests -v --tb=short --durations=10
```

## Tested runtime

- Linux x86-64 container, Ubuntu 24.04, Python 3.12.3, ROS 2 Jazzy.
- Gazebo Sim 8.15.0; gz-physics 7.8.0, explicit DART plugin selection.
- `ros-jazzy-gz-sim-vendor`: `0.0.13-1noble.20260905.073557`.
- `ros-jazzy-gz-physics-vendor`: `0.0.9-1noble.20260905.065116`.
- `ros-jazzy-simulation-interfaces`: `1.5.1-1noble.20260911.111314`.
- `ros-jazzy-rclpy`: `7.1.12-1noble.20260902.053513`.
- MuJoCo 3.15.0 and pytest 9.1.1 from the frozen Python lock.
- ROS base image digest is recorded in `integrations/ros2/Dockerfile`. Apt
  packages resolve at build time, so this is not a fully hermetic native toolchain.

## Limits and residual work

The fixture only covers the built-in contact-free cart. No external robot model,
GPU workload, contact-rich scene, native Windows/macOS ROS installation, remote
ROS network, or hostile-tenant deployment was validated. The existing dashboard
selection was extended; this slice verified its JavaScript syntax and backing API,
not a new browser end-to-end session. One upstream Starlette/httpx test-client
deprecation warning remains. ROS's unrelated bundled pytest plugins are disabled
in the verification image because they are incompatible with the newer pytest.

The implementation uses three ROS round trips per step plus dedicated process
startup. It makes no real-time or cross-platform bitwise repeatability promise.
API capability discovery reports its local installation, not worker readiness.
SQLite remains single-host. Broader runtime hardening and hosted scaling remain
separate milestones; this slice adds no deployment or release authority.
