# SW019 verification

Regression tests exercise parameter mapping, deterministic identities, independent
arithmetic checks, pass/fail counts, incomplete-pair handling, mutated/mismatched
inputs, CLI schemas/byte limits/non-overwrite and real reference/MuJoCo execution.
The full suite passed 365 tests, including nine new sweep-review regressions and
nine PostgreSQL tests against a disposable synthetic database. One existing
checkpoint symlink test was skipped because the host cannot create symlinks.
The existing Starlette/httpx deprecation warning remains. Ruff lint/format,
static/current-date strict governance checks, and offline wheel/source builds
passed. The disposable database was removed after testing.

No new ROS/Gazebo integration, cloud service, optimization or promotion is included.
Source summaries are structurally checked; raw telemetry verification remains a
separate bundle operation.
