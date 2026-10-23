# SW020 verification

Escaped hostile titles produce no executable tags or event attributes; CSP matches fixed CSS; metric values and evidence hashes match validated summaries; incomplete points withhold metrics; CLI validates before writing and refuses overwrite.

Full local validation passed: 368 tests including the three new HTML regressions,
real MuJoCo coverage and nine PostgreSQL tests against a disposable synthetic
database. One existing symlink checkpoint test was skipped because the host cannot
create symlinks. The existing Starlette/httpx deprecation warning remains.
Ruff lint/format, static/current-date strict governance checks and offline
wheel/source builds passed. The disposable database was removed after testing.

A synthetic report was rendered in Chromium at 1280- and 390-pixel viewport
widths. The fixed stylesheet applied under CSP, both point tables and the title
were present, no document overflow occurred at the narrow width, and no console
or page errors were observed. Screenshots were inspected locally.
No new ROS/Gazebo or cloud integration was exercised.

Limits: This is a derived descriptive report, not statistical inference, automatic optimization, baseline approval, signature authentication, raw telemetry validation or cross-engine accuracy proof. CSP is defense in depth; escaping is the primary HTML boundary. No browser or UI dependency enters simulation math. Very large accepted reports can be long; tables scroll horizontally on narrow screens.

