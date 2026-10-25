# SW021 validation

Deterministic CSV parses to the expected row count and columns; numeric round trips, source hashes and seed ordering match the review; hostile labels remain text-prefixed; incomplete metrics are blank; CLI preserves CRLF and refuses overwrite or invalid evidence.

Full local regression suite: 363 passed, 10 skipped. Four new CSV tests cover
precision and identity, hostile labels and quoting, incomplete evidence, exclusive
output and a real CLI subprocess with exact UTF-8/CRLF byte comparison. Existing
reference/MuJoCo tests ran. Ruff lint/format and static/current-date strict
governance checks passed. Offline source/wheel builds passed on the final code,
including the Windows stdout correction.

Nine PostgreSQL tests were skipped: the disposable database could not be started
because Docker's Linux engine was unavailable. One existing symlink checkpoint
test was skipped because host symlink creation was unavailable. The existing
Starlette/httpx deprecation warning remains. No spreadsheet application's later
save/reopen transformations, real ROS/Gazebo or cloud integration were exercised.

CSV is a derived view, not telemetry verification, inference or baseline approval. Consumers must preserve the text: prefix or explicitly import those columns as text; editing or stripping it changes the safety boundary. No universal safety guarantee is made for all spreadsheet programs or subsequent save/reopen transformations. Missing numeric values mean incomplete evidence, never zero. JSON remains the authoritative structured review format.

