# SW026 validation

Validated 2026-10-29 against the SW025 implementation branch.

- Full Python suite: 413 passed, ten skipped.
- Focused plan-comparison/export suite: 24 passed.
- Ruff lint and format checks: passed.
- Static and 2026-10-29 strict project governance: passed.
- Offline source/wheel builds passed; archive inspection found no private state directories.
- All 11 new export cases passed again after adding internally consistent count tampering.

The new tests cover v1 compatibility, v2 union order, added/removed adapter zero
counts, row/global sum invariants, signed reversal, schema versions, prefixed
hostile CSV labels, numeric round trips, exact UTF-8/CRLF stdout/files,
exclusive output, bounded inputs and read-only source verification. Reports
with altered names, identities, internally consistent counts or reversed
sources fail verification. No simulator is invoked by these commands.

Nine PostgreSQL integrations skipped because no test DSN was configured; one
existing host-symlink test skipped. MuJoCo coverage passed. The existing
Starlette/httpx deprecation warning remains. The first sandboxed full-suite
attempt was interrupted after hard-link denials; the complete rerun passed
with normal local filesystem access. Temporary test data stayed in ignored
project storage. No ROS/Gazebo execution or browser run was repeated; the
existing v1 HTML implementation is unchanged.
