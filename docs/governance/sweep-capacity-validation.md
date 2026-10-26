# SW023 validation

Remaining capacity reaches zero at each admission boundary; adapter totals equal workload totals in declared order. Default JSON is unchanged. Invalid/over-budget input produces no report, output never overwrites, hostile text is escaped, and contract constants reject non-integer values.

Local validation passed: 393 tests, including ten new capacity cases, real
MuJoCo coverage and nine PostgreSQL integrations against a disposable synthetic
database. One existing checkpoint symlink test was skipped because host symlink
creation was unavailable; the existing Starlette/httpx deprecation remains.
Ruff lint/format, static/current-date strict governance and offline source/wheel
builds passed. The disposable database was removed after testing.

Local Chromium desktop (1280px) and mobile (390px) smoke checks confirmed applied
CSP-authorized styles, expected report content, no scripts, no console errors
and no page overflow. The mobile screenshot was visually inspected. Hostile
text escaping is covered by the HTML regression. Gazebo-labelled planning does
not establish real Gazebo availability or execution.

Capacity is planned admission headroom, not reserved resources, adapter availability or a time/memory/storage/cost estimate. No simulation, queue scheduling or baseline decision occurs. Reports are unsigned derived evidence; execution independently validates its input.
