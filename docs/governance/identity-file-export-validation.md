# SW036 validation

Validated 2026-11-15.

Acceptance: `tests/test_identity_export.py`, `tests/test_bundle_html.py`.

Full pytest: 485 passed, 10 skipped (nine PostgreSQL checks without a configured DSN and one host symlink check). Ruff lint and format checks passed. Wheel and source distribution builds passed. The portable review example completed with HTML/CSV verified and no simulation.

Static and date-aware strict governance (`--as-of 2026-11-15 --strict`) passed.
Skipped optional checks are not passes. Hosted CI is assessed separately after push.
Python suites emitted an existing Starlette/httpx deprecation warning.
