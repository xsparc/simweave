# SW017 verification

Synthetic tests exercise two-tenant retained bytes, clean/mixed pages, continuation,
corruption, missing objects, backend unavailability, invalid inputs/metadata,
unchanged source state and CLI output/exit codes. The PostgreSQL integration suite
adds inventory pagination and tenant isolation against a disposable database.

Final full suite: 336 passed, one skipped. The skip is real symlink creation in
the existing checkpoint test, unavailable on the local host. All nine PostgreSQL
tests, including the new tenant/cursor inventory test, passed against the project's
pinned disposable PostgreSQL image with synthetic credentials. No live cloud
object store was contacted. Backend-unavailable behavior uses a synthetic adapter
failure; filesystem bytes and PostgreSQL queries are exercised directly.

The audit regressions also distinguish unavailable scratch storage from missing
objects and reject non-text digest metadata. Fixed diagnostics contain no raw
provider message. Ruff lint/formatting, strict governance validation, and wheel/source
distribution builds passed. The existing Starlette/httpx deprecation warning remains.

The disposable database was used only for synthetic tests and removed afterward.
No repair, pruning, production scan, deployment, or continuous monitoring occurred.
