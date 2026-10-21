# SW018 verification

Sweep regressions cover deterministic Cartesian order and Suite digests, unique
bounded names, unchanged base scenarios, mutated-model revalidation, closed axes,
finite values, duplicate rejection, scenario bounds, run/step caps, CLI schema,
stdout/file output and preservation of existing files. Generated suites execute
through the existing reference and installed MuJoCo adapters.

The full suite passed 356 tests, including all 20 sweep regressions and nine
PostgreSQL tests against the pinned disposable synthetic database. One existing
checkpoint symlink test was skipped because symlink creation is unavailable on
the host. The existing Starlette/httpx deprecation warning remains. Ruff lint and
format checks, static/current-date strict governance checks, and offline wheel
and source-distribution builds passed. The disposable database was removed.

Generated suites exercised 16 reference runs and eight real MuJoCo runs through
the existing bundle writer. No live ROS/Gazebo environment, cloud service,
adaptive tuning or promotion was exercised in this planning slice.
