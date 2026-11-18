# SW037 validation

Validated 2026-11-15.

Acceptance: `tests/test_identity_check.py`, `tests/test_bundle_html.py`.

Full pytest: 486 passed, 10 skipped (nine PostgreSQL checks without a configured DSN and one host symlink check). Ruff lint and formatting passed. Wheel and source-distribution builds passed. The portable synthetic HTML/CSV workflow passed under its no-simulation guard.

Static and date-aware strict governance (`--as-of 2026-11-15 --strict`) passed.
Skipped optional checks are not passes. Hosted CI is assessed separately after push.
An existing Starlette/httpx deprecation warning remains.
