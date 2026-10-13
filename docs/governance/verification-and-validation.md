# Verification and validation

## SW001

Run `python -m pytest tests/test_core.py` for strict inputs, seed isolation,
disturbance timing, gate failures, replay corruption, cleanup, and CLI round trip.
Run Ruff lint and format checks and the repository governance checker.
An executed result is recorded in each PR; this document describes the checks,
not an assertion that every future checkout has passed them.

2026-10-13 local SW001 verification: 23 tests passed on Python 3.12; Ruff lint
and format checks passed; the SimWeave static and dated strict evidence gates
passed. The upstream OpenSteward checker returned `project.identity` because its
project name is fixed; the repository-local gate retains SimWeave's actual identity.

## SW002

Exercise real headless MuJoCo separately from the ROS fake-transport suite.
Test concurrent claims, tenant isolation, idempotent submissions, cancellation,
lease expiry, restart persistence, telemetry pagination, and recording verification.

2026-10-13 local SW002 verification: 53 tests passed, including real MuJoCo
3.15.0 repeatability on Python 3.12. Ruff and static/dated strict governance
checks passed. One upstream Starlette/httpx test-client deprecation warning was
reported. ROS is covered by fake transport tests, not a live ROS environment.

## SW003

Run the full suite, build a wheel, inspect the package's static resources, exercise
the API/UI flow, and run the benchmark. Record container and real ROS checks as
unexecuted when the environment is unavailable. Cross-platform CI supplies
additional evidence after publication, not before it.

2026-10-13 SW003 local closeout: 56 tests passed; Ruff, JavaScript syntax,
static/dated strict governance, Python package builds, isolated wheel asset
checks, and Linux container execution passed. The browser exercised reference
and MuJoCo submission, playback, verification, and export; the exported recording
passed offline CLI replay. See `mvp-validation.md` for measurements and limits.
