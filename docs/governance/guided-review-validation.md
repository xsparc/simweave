# SW014 validation

2026-10-18: Chromium passed 20 approval/review cases across two tenants using real
local HTTP and 30 paired reference seeds. Tests cover reader/importer denial,
cross-tenant denial, keyboard cancellation/confirmation, concurrent generation
rejection, exact rollback policy and audit identity, recorded metric review,
disconnect clearing and read-only history. Late approval responses after disconnect
and mobile overflow checks also passed. Zero page errors.

The previous 30 browser workflows and six additional checks also passed. Full
pytest initially encountered an existing temporary-directory permission problem;
a fresh project-local test directory resolves setup. Final full suite: 297 passed,
eight PostgreSQL integration tests skipped because no test DSN was configured.
Installed MuJoCo tests passed. The existing Starlette/httpx deprecation warning
remains. Ruff lint/format, JavaScript syntax and static/dated strict governance
passed after indexing the new ADR. No product-code test failure remains.

No new live ROS/Gazebo, PostgreSQL, Keycloak or S3 validation is claimed. No
screen-reader certification, deployment, release or merge. Cross-platform browser
CI runs after publication and is separate from these local Chromium results.
