# SW022 validation

Counts independently equal expanded runs/steps for multiple axes/adapters/seeds; ordering and suite identity match the planner; no simulation is invoked; over-budget, invalid and mutated inputs fail; schema version is strict; CLI byte bounds and exclusive output hold.

Local validation passed: 383 tests, including 11 new workload-preview cases,
real MuJoCo coverage and nine PostgreSQL integrations against a disposable
synthetic database. One existing checkpoint symlink test was skipped because
host symlink creation was unavailable. The existing Starlette/httpx deprecation
warning remains. Ruff lint/format, static/current-date strict governance checks
and offline source/wheel builds passed.

Preview tests compare counts with independently expanded Suite cases and reject
simulation invocation. A Gazebo-labelled plan is inspected without requiring a
running Gazebo service. This does not validate real ROS/Gazebo execution or cloud
integration. The disposable database was removed after testing.

Counts are planned work, not wall-clock, memory, storage or monetary estimates. A valid plan does not establish installed adapter availability or successful execution. Rejected over-budget plans produce no partial report. Reports are unsigned derived evidence; execution must independently validate the Suite. No queue scheduling, simulation, automatic optimization or baseline decision occurs.

