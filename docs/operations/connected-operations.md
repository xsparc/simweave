# Connected review and recovery

Catalog HTTP uploads now retain their original ZIP before committing the build.
An immutable object may remain if catalog insertion fails; a successful new upload
never creates a reference before retaining its bytes. Existing imported catalogs
and legacy `history add` records are unchanged: retain their original bundles with
the operator `operations put` command before using artifact downloads/checkpoints.

The API defaults to filesystem objects beside its suite queue: with
`SIMWEAVE_DB=.simweave/runs.sqlite3`, the queue is `runs.sqlite3.suites`, its index
is `runs.sqlite3.suites.artifacts`, and objects are in `runs.sqlite3.suites.objects`.
Workers must use that queue and the same object directory. To use an existing
filesystem/S3 backend, set `SIMWEAVE_ARTIFACT_BACKEND` to the operator's backend
JSON file and pass the same file to workers with `--backend`. S3 credentials remain
explicit environment settings documented in the durable operations guide. No
request can choose a backend, database, credential or tenant.

## Job-to-review workflow

1. Submit a suite with a run token and wait for completion.
2. With a same-tenant catalog importer token, POST
   `/api/v1/catalog/builds/BUILD_LABEL/from-job` with
   `{"schema_version":1,"job":"JOB_ID","role":"candidate"}`.
3. Use existing catalog comparison and explicit baseline approval endpoints.
4. Catalog readers (including importer/approver roles) GET
   `/api/v1/catalog/builds/BUILD_LABEL/artifact` to download verified evidence.
   Run-token users GET `/api/v1/suite-jobs/JOB_ID/artifact` for their own job.

Catalog credentials do not gain execution rights; run credentials do not gain
baseline permissions. Cross-tenant resources return 404. Missing legacy bytes
return 404; unavailable/corrupt bytes return 503. Downloads verify the complete
bounded bundle into temporary storage before returning any bytes. At most two
downloads per API process hold verified snapshots concurrently; exhaustion returns
429. Response completion or send failure cleans up the snapshot and releases the
slot. Imports retain the existing two-operation concurrency bound. Suite completion
is distinct from scientific pass: comparisons may correctly be inconclusive.

## Metrics

Run-token users GET `/api/v1/suite-metrics` for v1 JSON containing only their
tenant's queue/status gauges, oldest queued age in seconds, and currently lost
worker jobs. Operator-wide metrics are CLI-only:

```sh
simweave operations --database .simweave/runs.sqlite3.suites metrics --backend storage.json
simweave operations --database .simweave/runs.sqlite3.suites metrics --backend storage.json --prometheus
```

Prometheus text uses fixed names, units and counter/gauge types without tenant,
token, subject, job-ID, object-key or worker-ID labels. An operator may pass this
text to their existing collector; no unauthenticated metrics endpoint is enabled.
Global metrics include cumulative lease losses, artifact put/get success/failure
counters, retained artifact count and workers with a heartbeat within 30 seconds.
Idle worker loops update heartbeats; active workers update at execution checkpoints
and during publication. Registry entries are capped at 1,024 and expire after an
hour. Heartbeat freshness is not proof that a simulator is healthy. Artifact
counters are best-effort if their metadata database itself is unavailable; they
count retrieval attempts, not successful client receipt. Lease-loss counters
survive explicit retries, while the lost-job gauge decreases on retry.

## Coordinated checkpoint and restore

The [operator workflow](operator-workflows.md) now offers a persistent admission
pause and automatic worker drain before checkpoint. The manual quiesced command
below remains supported. All fresh restores now start paused; explicitly run
`maintenance resume` against the restored suite queue after configuration checks.


Stop the API and workers, then resolve running jobs (expire/retry or cancel).
The explicit `--quiesced` flag acknowledges this operator prerequisite; the tool
also refuses running jobs and holds write reservations across existing catalogs,
queue and artifact metadata. Do not run independent writers or provision new
catalogs during this operation. Write reservations are a consistency guard, not
a live traffic-draining protocol.

```sh
simweave operations --database .simweave/runs.sqlite3.suites checkpoint recovery-point --backend storage.json --catalogs .simweave/runs.sqlite3.catalogs --quiesced
simweave operations --database unused.sqlite3 restore-checkpoint recovery-point restored-state
```

The checkpoint includes suite jobs, artifact index/counters, all catalogs under the
selected root, and all indexed artifact bytes (including retained orphans). It
validates catalog records and every referenced artifact. It hashes all files,
records a versioned manifest, verifies the complete snapshot, and publishes into a
fresh directory. A missing original bundle prevents completion; digests cannot
reconstruct lost bytes. The original legacy single-run queue is outside this suite
checkpoint; back it up separately if it is still used.

Restore validates hashes, database integrity, inventory, path restrictions and
references, copies bounded members to staging and verifies the actual copied bytes
again. It publishes only into a new destination, resets source worker presence,
and creates the standard API layout. Set `SIMWEAVE_DB` to
`restored-state/runs.sqlite3`, leave `SIMWEAVE_ARTIFACT_BACKEND` unset to use the
restored local objects, and supply the original identity mappings separately.
Configure workers to use `restored-state/runs.sqlite3.suites` and its `.objects`
sibling. Existing destinations are rejected; live state is never replaced.

These are trusted operator-local checkpoints, not signed interchange for untrusted
SQLite files. Hashes detect corruption, not an attacker who can rewrite both data
and manifest. Restrict access and keep an independent backup. Credentials, endpoints
and host configuration are excluded. Filesystem restore works regardless of the
original artifact backend; moving back to S3 is an explicit operator recovery step.

The acceptance drill (`scripts/check_connected_operations.py --output NEW_DIRECTORY`)
executes 100 authenticated job-to-comparison flows across two tenants, retains
1,000 distinct small reference bundles, checkpoints/restores 100 jobs plus catalog
history, verifies all references, and requires checkpoint plus restore to finish
within 300 seconds. This fixture target is not a full-sized production RTO.

Checkpoint limits: 99,000 indexed objects, 100 catalog files, a 16 MiB manifest
and 512 MiB per metadata file; existing 128 MiB bundle bounds remain. Capacity
and available disk space must be planned before copying large stores.
