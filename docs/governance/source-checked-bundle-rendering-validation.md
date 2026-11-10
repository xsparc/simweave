# SW032 validation

Validated 2026-11-10.

480 tests passed, 10 skipped (nine PostgreSQL tests without a DSN and one host symlink check). Installed MuJoCo coverage passed. Ruff lint and formatting passed. Existing Starlette/httpx deprecation remains; skipped optional checks are not passes.



Acceptance: `tests/test_source_checked_bundle_rendering.py`. Skipped optional checks are not passes. HTML layouts are unchanged.

Static governance and date-aware strict governance (`--as-of 2026-11-10 --strict`) passed.
Wheel and source distribution builds passed using installed dependencies; archive inventories exclude private state and environment directories.
