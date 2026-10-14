# Verification and validation

## SW007

2026-10-14: 163 portable tests and 16 live ROS/Gazebo conformance tests passed.
Reference, MuJoCo and Gazebo each completed positive and degraded 30-pair matrices
with repeatable intervals and expected decision exit codes. Twenty independently
recorded controller candidates remained pinned to one approved baseline; promotion,
rollback and reopened history passed. Lint, formatting, static/dated governance,
source/wheel packaging and installed-wheel checks passed. Browser static previews
showed the decision and approval history without console errors. See
`decisions-validation.md` for numerical results, runtime fingerprints and limits.

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

## SW004

2026-10-13 local closeout: 69 portable tests and 15 real ROS/Gazebo tests passed,
including MuJoCo comparisons, seeded repeatability, reset/isolation, native input
validation, lifecycle context handling, process faults, and CLI/API recording
replay. Ruff, JavaScript syntax, static/dated strict governance, source/wheel
builds, and wheel asset inspection passed. See `ros-gazebo-validation.md` for
the tested runtime, tolerance budgets, exact commands, and remaining limits.

## SW005

2026-10-13: 109 portable tests passed, along with the native two-controller,
ten-seed MuJoCo/Gazebo positive/negative matrix and all 16 live checks (the 15
original conformance tests plus an injected lost-discovery-response check).
The browser exercised comparison, imported suite review, failure navigation,
and JSON export. Ruff, JavaScript syntax, packaging, and governance checks passed.
The two-minute end-to-end usability target remains unverified due to file-dialog
automation delays. See `regression-validation.md` for actual evidence and gaps.

## SW006

2026-10-14: 129 portable tests passed. A known controller failure reproduced
exactly across fresh containers for reference, MuJoCo, and Gazebo (six original
and six rerun recordings). Offline static-preview navigation, hostile input, and
export contents were exercised; the actual downloaded JSON validated. Ruff,
JavaScript syntax, source/wheel builds, wheel asset inspection, and both governance
gates passed. Direct file-open and the two-minute end-to-end save target remain
unverified; see `evidence-validation.md` for the precise scope and limitations.

## SW008

2026-10-14: archive and tenant API verification is recorded in
`team-evidence-validation.md`, including the 100-build Windows/Linux recovery,
role isolation, approval concurrency and live example-client workflow. Existing
simulator and browser limitations remain explicitly separate.

## SW009

2026-10-14: 253 local tests passed, including RSA-signed OIDC authorization and
loopback JWKS lifecycle tests. Source/wheel builds and installed-wheel checks passed.
A real GitHub-attested 100-build catalog restored on Linux and Windows, with five
provenance/tampering negative controls rejected on both. Cryptographic results are
tracked separately from mocked boundary tests in `trusted-evidence-validation.md`.
