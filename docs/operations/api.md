# API and worker

Install `.[dev,mujoco]` to enable the reference and MuJoCo adapters. Use the same
environment for the API and worker. Start each in a separate terminal with the
same working directory or absolute `SIMWEAVE_DB` setting.

For `gazebo` jobs, install and source the [ROS/Gazebo fixture](ros2.md) in both
processes. The API rejects unavailable adapters before queueing. Capabilities
describe the API installation; they do not prove a worker is healthy. Each active
Gazebo worker owns one native fixture process. Bound worker counts and container
memory/CPU explicitly; the lightweight default image has no ROS.

Generate a fresh token locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Set `SIMWEAVE_TOKENS` to a JSON object mapping that token to a tenant name. Keep it
in environment/secrets management; do not commit it. Example structure:

```text
{"<generated-token>": "demo"}
```

On PowerShell, set `$env:SIMWEAVE_TOKENS` to the JSON string. On POSIX shells,
use `export SIMWEAVE_TOKENS='...'`. The server refuses an empty or invalid map.

```sh
simweave serve
# Separate terminal; worker does not need API tokens:
simweave worker
```

Open `http://127.0.0.1:8000/docs` for OpenAPI tools. `/healthz` is a process
liveness probe, not proof that a worker is available. No jobs execute until a
worker starts. `simweave worker --once` processes at most one queued job.

## Integration contract

Send `Authorization: Bearer <token>` on every `/api/v1` call. `POST /api/v1/runs`
accepts the scenario directly, returns 202 and a Location header. Repeating a
tenant-scoped `Idempotency-Key` with the same normalized scenario returns the
existing run (200); different input returns 409. Keys remain reserved until the
run is deleted. A deliberate rerun uses a new key.

Poll `GET /api/v1/runs/{id}`. Status transitions are queued -> running -> succeeded
or failed; queued/running can become cancelled. `succeeded` means execution
completed: inspect `result.passed` for quality gate outcome. Cancellation is
idempotent, terminal records remain terminal, and a worker cannot publish after
its claim expires or a run is cancelled. After restart, workers mark expired
claims failed with `worker_lost`; operators can resubmit explicitly.

List runs with `limit` (1-100) and `before` from `next_before`. Read telemetry with
`after` and `limit` (1-1000); `next_after` continues the scan. Each sample includes
its step, simulation time, position, velocity, observed position, controller
force, and disturbance force. Tenant-scoped indexes avoid a full telemetry scan.

`POST /api/v1/runs/{id}/verify` checks completed recording integrity and gates.
`GET /api/v1/runs/{id}/recording` streams portable NDJSON: one manifest containing
the scenario and result, followed by sample envelopes. Save as `recording.jsonl`
and run `simweave replay recording.jsonl` offline. No SaaS account is required.

`DELETE /api/v1/runs/{id}` removes a terminal run and its telemetry; cancel active
runs first. Recording export concurrent with deletion can be truncated and will
fail replay verification. Do not delete a run during export.

## Limits and operations

`GET /api/v1/comparisons?baseline={id}&candidate={id}` checks both tenant-owned
completed recordings and returns trajectory previews, signed metric deltas,
newly failing gate indices, and runtime warnings. Incomplete/corrupt recordings
return 409; different physical inputs return 422; hidden IDs return 404.

`POST /api/v1/suite-reports/compare` validates a bounded CLI `report.json` and
returns per-pair comparisons without persisting runs or executing physics. This
endpoint alone accepts up to 4 MiB. Imported summaries cannot verify omitted
telemetry. See the [regression guide](regression.md) for the contract and workflow.

Other request bodies: 64 KiB. Runs: 20 active and 1,000 retained per tenant, 64 active
globally. Scenarios: 20,000 steps. Up to 100 configured tokens. Use a gateway for
connection/read timeouts and request-rate limits. Per-tenant quotas protect queue
admission; scheduling is FIFO, not weighted tenant fairness.

SQLite WAL must be on one host and a local filesystem. Back up with SQLite's
backup API or stop writers before copying the database and its WAL together.
Delete terminal runs through the API for retention; offline VACUUM reclaims disk
space. Multiple workers can claim different runs on the same host, but database
write throughput remains shared. Use a process supervisor for workers. A hung
native simulator needs an operator/supervisor process timeout; leases prevent
late publication, not CPU termination. Arbitrary plugins are not supported.

Schema version 1 is recorded in SQLite `user_version`; unknown versions are
rejected. Future versions must ship explicit forward migrations and documented
backup/rollback instructions. Do not point older binaries at newer databases.

Internet hosting requires TLS, secret rotation, request limits, monitoring,
backup/restore testing, and a deployment-specific isolation review. OIDC,
distributed scheduling, object storage, and webhooks are deferred.
