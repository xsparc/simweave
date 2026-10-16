# Durable experiment operations

Suite jobs use the existing run-token authority. Catalog/OIDC credentials do not
gain execution permission. POST `/api/v1/suite-jobs` with a Suite v1 body and an
`Idempotency-Key` header (1–128 ASCII letters, digits, underscores or hyphens).
The response is a v1 job with status, attempt, suite digest and optional artifact
SHA-256 and review exit code. The same key and suite return the same job; a different
suite conflicts. GET the collection (limit 1–100, exclusive `after` job-ID cursor),
GET `/{id}`, POST `/{id}/cancel` or POST `/{id}/retry`.

Execution completion is distinct from scientific success: `succeeded` means the
suite produced a verified bundle; `exit_code` is 0 for passing, 1 for gate failure,
or 2 for simulator errors. Infrastructure/storage failure produces a failed job.

The API's queue database is the configured run database filename plus `.suites`.
Start workers with that exact path. Each worker processes one suite at a time;
start four independent copies of this command for four-way execution:

```sh
simweave operations --database .simweave/runs.sqlite3.suites worker --backend storage.json
```

Filesystem `storage.json`:

```json
{"schema_version":1,"root":".simweave/artifacts"}
```

S3-compatible configuration (install `simweave[s3]`):

```json
{"schema_version":1,"endpoint":"https://objects.example.org","bucket":"simweave-evidence","region":"us-east-1"}
```

Set only the explicitly named `SIMWEAVE_S3_ACCESS_KEY` and
`SIMWEAVE_S3_SECRET_KEY` environment variables in the worker's service environment.
No credential values belong in the JSON, command arguments or Git. The bucket must
already exist; SimWeave does not provision cloud resources. HTTPS is required
except numeric loopback HTTP for local verification. Proxies are disabled. Grant
GetObject/PutObject for the assigned prefix; DeleteObject is unnecessary. The
backend must honor conditional `If-None-Match: *` writes. Existing bytes are read
back and SHA-256 checked, never trusted through an ETag alone.

The queue and artifact index are separate local SQLite files; the artifact index
filename is the queue filename plus `.artifacts`. All worker processes must use
the same paths and backend, on one host with a local filesystem. Do not use NFS,
SMB or shared network volumes for SQLite. S3 storage does not enable multi-host
scheduling. Filesystem publication requires hard-link support (NTFS/ext4).

## CLI and recovery

```sh
simweave operations --database queue.sqlite3 submit suite.json --tenant team-a --key experiment-001
simweave operations --database queue.sqlite3 list --tenant team-a
simweave operations --database queue.sqlite3 show JOB_ID --tenant team-a
simweave operations --database queue.sqlite3 cancel JOB_ID --tenant team-a
simweave operations --database queue.sqlite3 retry JOB_ID --tenant team-a
simweave operations --database queue.sqlite3 get result.zip --tenant team-a --digest SHA256 --backend storage.json
simweave operations --database queue.sqlite3 put evidence.zip --tenant team-a --backend storage.json
simweave operations --database queue.sqlite3 recover replacement-storage.json --tenant team-a --backend storage.json
simweave operations --database queue.sqlite3 backup recovery-metadata --backend storage.json
```

CLI tenant selection is operator authority; restrict filesystem/service access.
The HTTP caller cannot select paths, tenants, credentials or storage endpoints.
Retrieved bundles can be imported into the existing baseline catalog using its
normal importer permissions; artifact storage itself never approves a baseline.
Catalog imports do not automatically copy their original ZIP into this store:
operators should retain it with `put` before discarding their source copy.

Stop submissions and workers before a coordinated backup. `backup` uses online
SQLite backup for each database, writing fresh `queue.sqlite3` and
`artifacts.sqlite3` files under the requested directory. The two snapshots are
not a cross-database transaction. Recover object bytes into a replacement backend
using the existing index, then copy the two backed-up metadata files to a fresh
queue path and its `.artifacts` sibling. Restart against that path and replacement
configuration. Never copy a live WAL database file alone. Verify retrieved bundles
with `bundle-check` before resuming. Recovery never overwrites existing files or
objects, and fails on missing/corrupted source bytes. Keep independent storage
backups/versioning: this operation cannot reconstruct lost bytes from digests.

Expired running jobs become `failed/worker_lost` when a worker claims work or an
operator requests retry. They are never silently executed again. Failed jobs can
be explicitly retried up to five total attempts. Cancellation is checked at sample
boundaries, throttled to 250 ms. A blocked adapter may remain alive until its own
timeout, but cancelled/expired attempts cannot commit success. During publication,
lease renewal runs for at most five minutes; an upload finishing after lease loss
can leave retained orphan evidence. Scratch directories from a forcibly killed
worker require operator cleanup after confirming no process is using them.

Limits: 1,000 retained jobs per tenant, 1,000 globally queued/running suite jobs,
10,000 indexed artifacts per tenant, 128 MiB per bundle and existing Suite limits
(64 runs / 200,000 steps). No deletion or garbage collection is exposed: all
objects, including referenced evidence and interrupted uploads, are retained.
Set disk/bucket monitoring and capacity limits operationally. External bucket
lifecycle rules or operator deletion can still remove evidence; disable such rules
for retained prefixes. Retention is application policy, not compliance object lock.

Run `python scripts/check_durable_operations.py --output CHECK_DIRECTORY` for
the 100-job/four-worker/two-tenant and 1,000-bundle recovery workload. Add
`--s3-config CONFIG` for an already provisioned local test bucket. CI uses a pinned
RustFS 1.0.0 container, synthetic credentials and loopback binding. No paid cloud
service is required, and compatibility with every S3 vendor is not claimed.


For explicitly configured PostgreSQL suite workers, see the
[provider/distributed guide](provider-distributed.md). The single-host restrictions
and SQLite backup commands above apply to the default SQLite backend.
