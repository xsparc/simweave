# Suite workspace and maintenance

Open **Suite workspace** from the dashboard. Supply a run token to submit, inspect,
cancel, retry and download jobs. Supply a catalog token to browse retained builds;
importers can import completed same-tenant jobs or upload ZIP evidence and compare
against the displayed approved baseline generation. Readers cannot import or
compare. Baseline imports never promote automatically; approval remains an
explicit catalog API action. An inconclusive statistical result is not a pass.

The suite editor accepts bounded version-1 JSON or a JSON file. Preserve the
idempotency key when retrying an uncertain submission; change it for a new job.
Refresh and inspect to see the latest status. Lists are paginated. Downloads use
verified retained bytes. Credentials are held in memory; disconnect or reload
clears them. Disconnect clears displayed evidence and cancels pending requests;
the suite draft remains editable. Native labeled controls, visible focus, status
announcements and keyboard navigation are supported. No identity provider login
flow or automatic polling is implied.

## Coordinated maintenance

Use the same suite queue and backend configuration as API/workers. All participating
processes must use the current version on one local host. Stop legacy catalog CLI
writers and external object/metadata writers first. The maintenance fence covers
suite submit/retry/claim, CLI artifact put and HTTP catalog mutations. Reads remain
available; active workers finish their current attempt. It does not include the
independent legacy experiment-run store in the checkpoint.

```sh
simweave operations --database state/runs.sqlite3.suites maintenance status
simweave operations --database state/runs.sqlite3.suites maintenance pause
simweave operations --database state/runs.sqlite3.suites maintenance drain --timeout 300
simweave operations --database state/runs.sqlite3.suites maintenance checkpoint --backend storage.json --catalogs state/runs.sqlite3.catalogs --output checkpoints/first
simweave operations --database state/runs.sqlite3.suites maintenance resume
```

`checkpoint` automatically pauses and drains when invoked without prior steps.
Pause waits up to five seconds for already admitted catalog/queue operations;
if busy, retry and inspect status. Drain timeout is bounded to 0..3600 seconds.
Failed drain or checkpoint leaves admission paused. Successful checkpoint also
leaves it paused so an operator can review results before resuming. Checkpoint
output must be a fresh path; an interrupted unpublished copy can be retried at
that path. If publication completed before interruption, verify/restore that
checkpoint or choose a new path; never overwrite it.

Drain refuses unresolved running jobs or busy workers, including cancelled jobs
still unwinding. If a worker crashed, stop **all** source workers and wait for
outstanding leases to expire before explicitly acknowledging stopped workers:

```sh
simweave operations --database state/runs.sqlite3.suites maintenance acknowledge-stopped --workers-stopped
simweave operations --database state/runs.sqlite3.suites maintenance drain
```

This assertion removes stale worker presence and marks expired attempts failed.
It does not retry jobs or resume admission. Never assert workers stopped while
any worker could still write. After resume, failed jobs remain available for
explicit bounded retry.

```sh
simweave operations --database state/runs.sqlite3.suites restore-checkpoint checkpoints/first recovered
simweave operations --database recovered/runs.sqlite3.suites maintenance status
simweave operations --database recovered/runs.sqlite3.suites maintenance resume
```

Restore verifies every metadata/object hash and all references, writes a fresh
runtime directory, clears worker presence and starts **paused**. Configure the
new API with `SIMWEAVE_DB=recovered/runs.sqlite3`; credentials and backend config
are supplied separately. Restored objects use the filesystem backend. Do not run
both source and restored queues as the same logical service. Reserve space for
source, checkpoint and restored bytes; this is a full copy, not deduplicated or
incremental backup. Process-interruption tests do not certify hardware power-loss
behavior.

## Reproduce validation

```sh
uv sync --frozen --extra dev --extra browser
uv run --frozen --extra dev --extra browser python -m playwright install chromium
uv run --frozen --extra dev --extra browser python scripts/check_browser_workspace.py --output .simweave/browser
uv run --frozen --extra dev python scripts/check_operator_recovery.py --output .simweave/recovery --gib 10
```

The volume drill writes at least 10 GiB of physical ZIP_STORED bytes with distinct
ZIP dates, all derived from a semantically verified recording bundle. It populates
synthetic terminal job references, injects interruption after pause, during object
copy and after publication, then verifies recovery and explicit resume. It measures
storage recovery rather than simulation throughput. The four-worker live drain is
a separate regression test. CI uses a small volume fixture; the full-size local
measurement is recorded in the validation evidence.
