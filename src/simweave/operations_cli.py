"""Explicit operator configuration and machine-readable durable operations."""

import os
from pathlib import Path

from simweave.artifacts import S3, Artifacts, Filesystem, backup_database
from simweave.contracts import Contract, canonical
from simweave.suite_jobs import SuiteJobs, work_forever, work_once
from simweave.suites import Suite


class BackendConfig(Contract):
    schema_version: int = 1
    root: str | None = None
    endpoint: str | None = None
    bucket: str | None = None
    region: str = "us-east-1"


def backend(path: Path):
    if path.stat().st_size > 4096:
        raise ValueError("backend configuration exceeds 4 KiB")
    config = BackendConfig.model_validate_json(path.read_bytes())
    if config.schema_version != 1:
        raise ValueError("unsupported backend configuration")
    if config.root and config.endpoint is None and config.bucket is None:
        return Filesystem(Path(config.root))
    if config.root is None and config.endpoint and config.bucket:
        return S3(
            endpoint=config.endpoint,
            bucket=config.bucket,
            region=config.region,
            access_key=os.environ["SIMWEAVE_S3_ACCESS_KEY"],
            secret=os.environ["SIMWEAVE_S3_SECRET_KEY"],
        )
    raise ValueError("configure exactly one storage backend")


def register(commands):
    operation = commands.add_parser("operations", help="durable suites and immutable artifacts")
    operation.add_argument("--database", type=Path, required=True, help="suite queue database")
    sub = operation.add_subparsers(dest="operation", required=True)
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
    for action in ("put", "get", "recover", "backup"):
        command = sub.add_parser(action)
        command.add_argument("--backend", type=Path, required=True)
        command.add_argument("path", type=Path)
        if action != "backup":
            command.add_argument("--tenant", required=True)
        if action == "get":
            command.add_argument("--digest", required=True)


def artifact_database(queue: Path):
    return queue.with_name(queue.name + ".artifacts")


def dispatch(args):
    jobs = SuiteJobs(args.database)
    action = args.operation
    if action == "submit":
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
        artifacts = Artifacts(artifact_database(args.database), backend(args.backend))
        if action == "worker":
            if not args.once:
                work_forever(jobs, artifacts)
                return 0
            result = {"worked": work_once(jobs, artifacts)}
        elif action == "put":
            result = {"digest": artifacts.put(args.tenant, args.path)}
        elif action == "get":
            artifacts.get(args.tenant, args.digest, args.path)
            result = {"retrieved": True}
        elif action == "recover":
            result = {"recovered": artifacts.recover(args.tenant, backend(args.path))}
        else:
            # Separate snapshots: stop workers/submissions for a consistent recovery point.
            args.path.mkdir(parents=True, exist_ok=False)
            artifacts.backup(args.path / "artifacts.sqlite3")
            backup_database(jobs.db, args.path / "queue.sqlite3")
            result = {"backed_up": True}
    print(canonical(result))
    return 0
