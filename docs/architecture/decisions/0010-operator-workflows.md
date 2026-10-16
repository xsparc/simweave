# ADR 0010: Operator workflows and persistent maintenance

Status: accepted

Date: 2026-10-16

Baseline: `48474cba23b636d251f036597a0e5d8c1bdb8151`.
The maintainer accepted recommendations 1 and 2 after PR16's squash merge.
SW012 delivers browser suite submission, inspection, cancellation, retained downloads,
job/bundle import and pinned-generation comparison in one workspace. Credentials
remain in memory; disconnect invalidates outstanding responses and clears evidence.
Native labeled controls and live status support keyboard operation. Existing roles
remain separate; imports never implicitly approve a baseline.

Persist a single-host admission fence beside the queue. SQLite rollback-journal
read transactions cover submissions, claims, retries, CLI puts and HTTP catalog
mutations. Pause commits only after admitted operations finish. Active workers
finish their current jobs; no subsequent claim crosses the fence. Drain waits for
both running jobs and busy workers, including cancelled jobs still unwinding.
Timeouts and interruption leave admission paused. Checkpoint holds the paused fence
through verified publication; resume is explicit. Restores start paused. Direct
legacy catalog CLI writers and backend administrators must remain stopped during
maintenance. No filesystem lock claims cover uncooperative external writers.

Acceptance: 30 browser workflow cases across two tenants, keyboard controls,
four-worker drain, a real 10 GiB retained-byte recovery fixture, three interruption
points with no lost references, and measured recovery time. Expected paths: static
workspace, maintenance/queue/catalog/CLI/recovery, tests and validation scripts,
CI and operator/governance documentation. Risks: stale workers, disk exhaustion,
credential replacement races, interrupted copies and external writers. Fail closed
on unresolved busy workers; never silently discard their authority.

Non-scope: multi-host scheduling, automatic promotion, provider provisioning,
release/deployment, retention deletion and a new identity role.
