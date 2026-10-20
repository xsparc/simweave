"""Explicit operator configuration and machine-readable durable operations."""

from pathlib import Path

from simweave.artifacts import Artifacts, backup_database
from simweave.contracts import canonical
from simweave.storage_config import artifact_database, backend
from simweave.suite_jobs import SuiteJobs, work_forever, work_once
from simweave.suites import Suite


def register(commands):
    operation = commands.add_parser("operations", help="durable suites and immutable artifacts")
    operation.add_argument("--database", type=Path, required=True, help="suite queue database")
    operation.add_argument(
        "--postgres", action="store_true", help="use explicit PostgreSQL DSN from environment"
    )
    sub = operation.add_subparsers(dest="operation", required=True)
    sub.add_parser("initialize", help="initialize fresh PostgreSQL schema version 1")
    for action in ("submit", "show", "list", "cancel", "retry"):
        command = sub.add_parser(action)
        command.add_argument("--tenant", required=True)
        if action == "submit":
            command.add_argument("path", type=Path)
            command.add_argument("--key", required=True)
        elif action != "list":
            command.add_argument("id")
        else:
            command.add_argument("--after", default="")
    worker = sub.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--backend", type=Path, required=True)
    metrics = sub.add_parser("metrics", help="operator-wide metrics without tenant labels")
    metrics.add_argument("--backend", type=Path, required=True)
    metrics.add_argument("--prometheus", action="store_true")
    audit = sub.add_parser("audit", help="check one bounded page of retained artifact bytes")
    audit.add_argument("--backend", type=Path, required=True)
    audit.add_argument("--tenant", required=True)
    audit.add_argument("--after", default="")
    audit.add_argument("--limit", type=int, default=10)
    checkpoint = sub.add_parser("checkpoint", help="snapshot quiesced suites, catalogs and bytes")
    checkpoint.add_argument("--backend", type=Path, required=True)
    checkpoint.add_argument("--catalogs", type=Path, required=True)
    checkpoint.add_argument("--quiesced", action="store_true", required=True)
    checkpoint.add_argument("path", type=Path)
    checkpoint.add_argument("--object-cache", type=Path, help="immutable same-volume object cache")
    restore = sub.add_parser("restore-checkpoint", help="verify and restore into a fresh directory")
    restore.add_argument("source", type=Path)
    restore.add_argument("path", type=Path)
    maintenance = sub.add_parser(
        "maintenance", help="pause, drain, checkpoint and explicitly resume"
    )
    maintenance.add_argument(
        "action",
        choices=("status", "pause", "drain", "resume", "checkpoint", "acknowledge-stopped"),
    )
    maintenance.add_argument("--workers-stopped", action="store_true")
    maintenance.add_argument("--timeout", type=float, default=300)
    maintenance.add_argument("--backend", type=Path)
    maintenance.add_argument("--catalogs", type=Path)
    maintenance.add_argument("--output", type=Path)
    maintenance.add_argument("--object-cache", type=Path, help="immutable same-volume object cache")
    for action in ("put", "get", "recover", "backup"):
        command = sub.add_parser(action)
        command.add_argument("--backend", type=Path, required=True)
        command.add_argument("path", type=Path)
        if action != "backup":
            command.add_argument("--tenant", required=True)
        if action == "get":
            command.add_argument("--digest", required=True)


def dispatch(args):
    if args.operation == "restore-checkpoint":
        if args.postgres:
            raise ValueError("SQLite restore cannot target PostgreSQL")
        from simweave.recovery import restore

        print(canonical(restore(args.source, args.path)))
        return 0
    if args.postgres:
        from simweave.postgres import Database, Jobs

        database = Database(args.database.parent, initialize=args.operation == "initialize")
        try:
            return dispatch_jobs(args, Jobs(database))
        finally:
            database.close()
    return dispatch_jobs(args, SuiteJobs(args.database))


def artifacts_for(args, jobs):
    if args.postgres:
        from simweave.postgres import SharedArtifacts

        return SharedArtifacts(jobs.database, backend(args.backend))
    return Artifacts(artifact_database(args.database), backend(args.backend))


def dispatch_jobs(args, jobs):
    action = args.operation
    if action == "initialize":
        if not args.postgres:
            raise ValueError("initialize requires --postgres")
        print(canonical({"schema_version": 1, "initialized": True}))
        return 0
    if action == "maintenance":
        from simweave import maintenance

        if args.action == "status":
            result = {"schema_version": 1, "paused": jobs.gate.paused()}
        elif args.action in ("pause", "resume"):
            result = jobs.gate.set(args.action == "pause")
        elif args.action == "acknowledge-stopped":
            result = maintenance.acknowledge_stopped(jobs, args.workers_stopped)
        elif args.action == "drain":
            result = maintenance.drain(jobs, args.timeout)
        else:
            if not all((args.backend, args.catalogs, args.output)):
                raise ValueError("checkpoint requires backend, catalogs and output")
            artifacts = artifacts_for(args, jobs)
            result = maintenance.checkpoint(
                jobs,
                artifacts,
                args.catalogs,
                args.output,
                args.timeout,
                object_cache=args.object_cache,
            )
    elif action == "submit":
        if args.path.stat().st_size > 65536:
            raise ValueError("suite exceeds 64 KiB")
        result = jobs.submit(
            args.tenant, Suite.model_validate_json(args.path.read_bytes()), args.key
        )
    elif action in ("show", "cancel", "retry"):
        result = getattr(jobs, "get" if action == "show" else action)(args.tenant, args.id)
        if result is None:
            raise KeyError("job not found")
    elif action == "list":
        result = jobs.list(args.tenant, args.after)
    else:
        artifacts = artifacts_for(args, jobs)
        if action == "audit":
            from simweave.integrity import audit

            result = audit(artifacts, args.tenant, after=args.after, limit=args.limit)
            print(canonical(result))
            return 0 if result["healthy"] else 1
        elif action == "metrics":
            from simweave.observability import prometheus, snapshot

            result = snapshot(jobs, artifacts)
            if args.prometheus:
                print(prometheus(result), end="")
                return 0
        elif action == "checkpoint":
            from simweave.recovery import checkpoint

            result = checkpoint(
                jobs, artifacts, args.catalogs, args.path, object_cache=args.object_cache
            )
        elif action == "worker":
            if not args.once:
                work_forever(jobs, artifacts)
                return 0
            result = {"worked": work_once(jobs, artifacts)}
        elif action == "put":
            with jobs.gate.hold():
                result = {"digest": artifacts.put(args.tenant, args.path)}
        elif action == "get":
            artifacts.get(args.tenant, args.digest, args.path)
            result = {"retrieved": True}
        elif action == "recover":
            result = {"recovered": artifacts.recover(args.tenant, backend(args.path))}
        else:
            if args.postgres:
                raise ValueError("use PostgreSQL-native backup")
            # Separate snapshots: stop workers/submissions for a consistent recovery point.
            args.path.mkdir(parents=True, exist_ok=False)
            artifacts.backup(args.path / "artifacts.sqlite3")
            backup_database(jobs.db, args.path / "queue.sqlite3")
            result = {"backed_up": True}
    print(canonical(result))
    return 0
