# SW033 validation

Validation date: 2026-11-11.

Acceptance: `tests/test_bundle_html.py`.

483 tests passed, 10 skipped (nine PostgreSQL tests without a DSN and one host symlink check). Installed MuJoCo coverage passed. The standalone portable example passed without simulation. Ruff lint and formatting passed.

Static and date-aware strict governance (`--as-of 2026-11-11 --strict`) passed.


Wheel and sdist builds passed; archive inventories exclude private state and environment directories. Existing Starlette/httpx deprecation remains. Skips are not passes.

HTML layouts are unchanged. No browser execution, deployment or device-performance validation was performed.
