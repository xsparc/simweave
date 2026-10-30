# SW027 validation

Validated 2026-10-31 on main after merged SW026.

- Full Python suite: 423 passed, ten skipped.
- Focused portable-review and prior export suites: 21 passed.
- Ruff lint and format checks: passed.
- Chromium at 1280x900 and 390x900: two visible review tables, no page overflow,
  escaped script-shaped label, no script execution or page errors. Mobile
  screenshot inspected; the adapter table scrolls within its container.

The portable fixture preserves total workload but changes adapter membership and
seed identity. Tests exercise JSON v1/v2, HTML v1/v2 and CSV with simulation
execution forbidden. CSV failures cover cells, headers, row order, missing/extra
rows, direction, UTF-8, byte size and noncanonical newlines. Source files remain
unchanged and no evidence is repaired.

Nine PostgreSQL integrations skipped without a test DSN; one existing host
symlink test skipped. MuJoCo tests passed. No native ROS/Gazebo execution was
performed. Existing Starlette/httpx deprecation remains. The suite ran with
normal local filesystem permissions for existing hardlink tests.

Static and 2026-10-31 strict project governance checks passed.
Offline source and wheel builds passed. Archive member inspection found no
private state directories.
