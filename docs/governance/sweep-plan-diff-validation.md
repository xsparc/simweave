# SW025 validation

Direction reversal negates deltas; adapter additions/removals preserve declared order; identical inputs are explicit and changed experiments with equal counts are not called identical. Both mutated/over-budget sources fail before rendering. Contracts reject inconsistent summaries and noninteger schema versions. CLI rejects oversized inputs without output and never overwrites. HTML preserves JSON identities/counts, escapes hostile names and passes desktop/mobile checks.

Local validation passed: 411 tests including 13 new comparison cases, installed
MuJoCo coverage and nine PostgreSQL integrations against a disposable synthetic
database. One existing checkpoint symlink test skipped because host symlink
creation was unavailable; the existing Starlette/httpx deprecation remains.
Ruff lint/format, static/current-date strict governance and offline source/wheel
builds passed. The disposable database was removed after testing.

Local Chromium checks at 1280px and 390px confirmed applied CSP-authorized CSS,
expected comparison rows, no scripts, no console errors and no page overflow.
Mobile rendering was visually inspected and table spacing improved; all 13
comparison tests and browser checks passed again afterward. No local real
ROS/Gazebo execution was rerun. HTML hostile-label and CSP-hash regressions pass.

Reports compare planned counts, not execution results, physics equivalence, availability, reservations or runtime estimates. Identical inputs means equal normalized Sweep digests. Internal report consistency is not proof of source provenance; comparisons must be generated from independently admitted inputs. No simulation, scheduling, optimization or baseline approval occurs.
