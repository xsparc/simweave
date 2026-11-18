# SW038 validation

Validation date: 2026-11-18.
Acceptance: `tests/test_verification_scope.py`.

Full pytest: 487 passed, 10 skipped (nine PostgreSQL checks without DSN and one host symlink check). Ruff lint/format and wheel/source-distribution builds passed. Verification scope combinations and replacement rejection passed. Evidence review freshness was renewed after architecture/roadmap/traceability review; live ROS/container/S3/PostgreSQL checks were not rerun.

Static and date-aware strict governance (`--as-of 2026-11-18 --strict`) passed.
Skipped checks are not passes. Hosted CI is assessed separately after push.
An existing Starlette/httpx deprecation warning remains.
