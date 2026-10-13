# MVP validation, 2026-10-13

## Executed evidence

- SW001: 23 local tests; Linux, Windows, and macOS CI on Python 3.11/3.12 passed.
- SW002: 53 local tests including real MuJoCo 3.15.0; the same six-platform/version
  CI matrix and a Linux MuJoCo job passed.
- SW003 before final publication: full pytest suite, Ruff lint/format, dated
  strict traceability, JavaScript syntax, standard Python source/wheel builds,
  and package asset checks. Final counts are recorded in PR 3.
- Browser: connected the authenticated dashboard, ran the reference and real
  MuJoCo recovery scenarios, observed successful completion and gates, verified
  recordings, played telemetry, scrubbed to the final sample, and exported JSONL.
  The browser-exported recording passed offline CLI replay verification.
- Responsive browser check: corrected an overflow caused by an offscreen table
  label; the mobile page's measured content and viewport widths both equal
  375 CSS pixels. Reload confirmed that the token was not persisted.
- The installed `simweave demo` entrypoint served its API and its separately
  spawned worker completed a test experiment. The temporary demo was stopped.
- Container: built the Linux image from hash-pinned runtime dependencies; ran real
  headless MuJoCo; served the packaged dashboard/API on loopback; submitted a
  MuJoCo run, processed it with the worker, and verified the result through HTTP.
  The temporary smoke-test container was stopped and removed.
- Compose configuration validated. The complete two-service Compose deployment
  was not started; its components were exercised in the temporary container.

## Measured performance

The benchmark executed 20,000 steps three times per adapter with Python allocation
tracking enabled. The median reference run was 0.7839 seconds (25,515 steps/s);
MuJoCo was 1.7597 seconds (11,365 steps/s). Peak tracked Python allocation was
26,134 bytes for reference and 8,633,053 bytes for MuJoCo, including import/setup.
These are one environment's observations, not guarantees. Native allocations,
database I/O, HTTP traffic, and rendering are not included. Reproduce with
`python scripts/benchmark.py --adapter reference` and `--adapter mujoco`.

## Known limits

No real ROS/Gazebo environment was available. ROS uses transport contract tests;
full robot experiments through ROS are outside the MVP. Multi-host workers,
OIDC onboarding, object storage, hard real-time guarantees, and cross-simulator
bitwise identity are not implemented. One upstream Starlette warning recommends
the newer httpx2 test client; current httpx tests pass across the CI matrix.

OpenSteward's installed checker rejects any project identity other than its own.
Its run returned only `project.identity` for SimWeave; SimWeave's local static and
strict evidence gates are used without relabeling the project.
