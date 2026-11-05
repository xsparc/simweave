# SW029 validation

Validated 2026-11-05.

454 tests passed, ten skipped (nine PostgreSQL tests without a DSN and one host symlink test). MuJoCo tests passed. Ruff lint and formatting passed.

Acceptance: `tests/test_bundle_verification.py` covers the new retained-evidence contract. Existing suites cover strict intake and source consistency. No timing assertions or new attestation claims.

Existing Starlette/httpx deprecation remains; optional runtime/service skips are not passes.

Project-specific static and 2026-11-05 strict governance checks passed. Diff whitespace and public-file privacy scans passed. Offline wheel/source builds passed; archive inspection found no private state.
