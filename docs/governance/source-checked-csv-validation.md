# SW034 validation

Validation date: 2026-11-12.
Acceptance: `tests/test_bundle_html.py`.

484 tests passed, 10 skipped (nine PostgreSQL tests without a DSN and one host symlink check). Installed MuJoCo coverage passed. Ruff lint and formatting passed.

Static and date-aware strict governance (`--as-of 2026-11-12 --strict`) passed.

Wheel and sdist builds passed; archive inventories exclude private state and environments. Existing Starlette/httpx deprecation remains. Skips are not passes.

HTML layouts remain unchanged. No browser execution, deployment or physical-device performance claims.
