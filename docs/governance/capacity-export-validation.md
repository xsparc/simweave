# SW024 validation

Generated schema exposes closed nested contracts and shared limits. CSV round-trips hostile labels, sums adapter totals correctly, preserves identities/order and exact CLI bytes, and never overwrites files. Invalid and over-budget plans fail before output. Existing capacity boundary and full suite tests pass.

Local validation passed: 398 tests, including five new export cases, installed
MuJoCo tests and nine PostgreSQL integrations against a disposable synthetic
database. One existing checkpoint symlink test skipped because host symlink
creation was unavailable. The existing Starlette/httpx deprecation remains.
Ruff lint/format, static/current-date strict governance and offline source/wheel
builds passed. The disposable database was removed.

CLI subprocess tests verify exact UTF-8/CRLF bytes and exclusive creation.
No spreadsheet application was used to claim formula-execution safety after
editing/re-saving exports. HTML styling was unchanged and was not rechecked
in a browser this iteration. Real ROS/Gazebo execution was not rerun locally.

CSV headroom is for the entire plan and is repeated on each adapter row; it is not per-adapter quota and must not be summed. Labels are deliberately prefixed; stripping the prefix can reintroduce spreadsheet formula risks. JSON Schema describes structure, not proof that a report derives from a valid plan. Reports remain unsigned planned counts, without execution, availability checks or resource estimates.
