# Audit retained artifact bytes

Run `simweave operations --database queue audit --backend backend.json --tenant alpha`.
Use the existing explicit backend configuration. Add `--postgres` before `audit`
for the configured shared database. No cloud credentials are discovered implicitly.

The command checks a page of 10 objects by default; `--limit` accepts 1..25.
Feed the JSON `next_after` into `--after` until it is null. Exit 0 means every
object on this page verified, including an empty page; exit 1 reports one or more
failures; exit 2 indicates command/metadata validation failure. Always inspect
pagination: a healthy first page does not certify the whole inventory.

Each result gives digest, expected bytes and one status: verified, corrupt,
missing (local file absent), or unavailable (I/O/provider failure). S3 failures
are unavailable, including possible missing objects, so access denial is never
misreported as confirmed absence. Error details and local paths are not included.
Reports include the explicitly selected tenant and artifact digests; store them
with the same access restrictions as other operator evidence.

The audit compares retained SHA-256/size, not ZIP semantics, recording replay,
signature provenance or catalog reference completeness. It does not alter source
objects or retained metadata, repair damage, delete orphans or promote baselines.
Take an independent backup and investigate failures using explicit operator tools.

Objects are streamed through temporary storage one at a time with the existing
128 MiB object cap. A 25-object page may read up to 3.125 GiB, plus bounded read
lookahead; provision scratch space and choose a smaller page for slow storage.
There is no page wall-clock SLA. Failed objects still advance the page cursor;
restart from an earlier cursor to recheck them after an operator repair.

Database transactions end before downloads. The inventory page is fixed at query
time, but the entire multi-page scan is not a snapshot. New objects sorting before
the cursor can be missed. For a fixed inventory, pause and drain writers using the
existing maintenance procedure; resume is explicit. Otherwise repeat scans from
the beginning. The command itself never changes the maintenance fence.
