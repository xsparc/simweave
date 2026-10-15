"""Coordinated operator-local checkpoints, verified before fresh-directory restore."""

import hashlib
import json
import os
import re
import sqlite3
import tempfile
import time
from contextlib import ExitStack, closing
from pathlib import Path

from simweave import history
from simweave.artifacts import backup_database, digest_file, key
from simweave.contracts import canonical


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def readonly(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA trusted_schema=OFF")
    return closing(connection)


def inventory(root):
    with readonly(root / "artifacts.sqlite3") as db:
        if db.execute("SELECT count(*) FROM artifacts").fetchone()[0] > 99000:
            raise ValueError("checkpoint artifact limit exceeded")
        objects = {
            (tenant, digest): size
            for tenant, digest, size in db.execute("SELECT tenant,digest,size FROM artifacts")
        }
    with readonly(root / "queue.sqlite3") as db:
        if db.execute("SELECT count(*) FROM suite_jobs_v1 WHERE status='running'").fetchone()[0]:
            raise ValueError("checkpoint contains running jobs")
        references = set(
            db.execute("SELECT tenant,artifact FROM suite_jobs_v1 WHERE artifact IS NOT NULL")
        )
        jobs = db.execute("SELECT count(*) FROM suite_jobs_v1").fetchone()[0]
    for catalog in sorted((root / "catalogs").glob("tenant-*.sqlite3")):
        tenant = catalog.name[len("tenant-") : -len(".sqlite3")]
        key(tenant, "0" * 64)
        with history._connect(catalog) as db:
            for table, limit in (
                ("builds", history.MAX_BUILDS),
                ("events", history.MAX_EVENTS),
                ("comparisons", history.MAX_COMPARISONS),
            ):
                if db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] > limit:
                    raise ValueError("catalog limits exceeded")
            for row in db.execute("SELECT label FROM builds"):
                references.add((tenant, history._build(db, row[0]).bundle_digest))
            for row in db.execute("SELECT generation FROM events"):
                history._event(db, row[0])
            for row in db.execute("SELECT digest,payload FROM comparisons"):
                history._decode(row, history.BuildComparison)
    if not references <= objects.keys():
        raise ValueError("missing referenced artifact metadata")
    for (tenant, digest), size in objects.items():
        key(tenant, digest)
        if type(size) is not int or not 0 < size <= 128 * 1024 * 1024:
            raise ValueError("invalid artifact metadata")
    return objects, references, jobs


def checkpoint(jobs, artifacts, catalogs: Path, target: Path):
    """Caller must stop API/workers first; lock reservations enforce metadata stability."""
    if target.exists():
        raise FileExistsError("checkpoint target exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        staged = Path(temporary) / "checkpoint"
        staged.mkdir()
        (staged / "catalogs").mkdir()
        (staged / "objects").mkdir()
        paths = sorted(catalogs.glob("tenant-*.sqlite3")) if catalogs.exists() else []
        if len(paths) > 100:
            raise ValueError("catalog capacity exceeded")
        with ExitStack() as locks:
            # Catalog -> queue -> artifact: callers never hold reverse-order writes.
            for path in paths:
                locks.enter_context(history._connect(path, write=True))
            queue = locks.enter_context(jobs.db.connect())
            queue.execute("BEGIN IMMEDIATE")
            if queue.execute(
                "SELECT count(*) FROM suite_jobs_v1 WHERE status='running'"
            ).fetchone()[0]:
                raise ValueError("stop workers and resolve running jobs before checkpoint")
            index = locks.enter_context(artifacts.db.connect())
            index.execute("BEGIN IMMEDIATE")
            backup_database(jobs.db, staged / "queue.sqlite3")
            backup_database(artifacts.db, staged / "artifacts.sqlite3")
            for path in paths:
                with (
                    readonly(path) as source,
                    closing(sqlite3.connect(staged / "catalogs" / path.name)) as destination,
                ):
                    source.backup(destination)
            objects, references, count = inventory(staged)
            for (tenant, digest), size in objects.items():
                destination = staged / "objects" / key(tenant, digest)
                destination.parent.mkdir(parents=True, exist_ok=True)
                artifacts.backend.get(key(tenant, digest), destination)
                if digest_file(destination) != (digest, size):
                    raise ValueError("checkpoint object failed verification")
            files = {
                str(path.relative_to(staged)).replace("\\", "/"): {
                    "sha256": sha(path),
                    "size": path.stat().st_size,
                }
                for path in staged.rglob("*")
                if path.is_file()
            }
            manifest = {
                "schema_version": 1,
                "files": files,
                "jobs": count,
                "artifacts": len(objects),
                "references": len(references),
            }
            (staged / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
        verify(staged)
        if target.exists():
            raise FileExistsError("checkpoint target exists")
        os.rename(staged, target)
    return {
        "schema_version": 1,
        "jobs": count,
        "artifacts": len(objects),
        "references": len(references),
        "seconds": round(time.monotonic() - started, 3),
    }


def verify(root: Path):
    manifest = root / "manifest.json"
    if manifest.is_symlink() or manifest.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("invalid checkpoint manifest")

    def unique(pairs):
        result = {}
        for name, item in pairs:
            if name in result:
                raise ValueError("duplicate checkpoint field")
            result[name] = item
        return result

    value = json.loads(manifest.read_bytes(), object_pairs_hook=unique)
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "files", "jobs", "artifacts", "references"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or not isinstance(value["files"], dict)
        or len(value["files"]) > 100000
        or any(
            type(value[n]) is not int or value[n] < 0 for n in ("jobs", "artifacts", "references")
        )
    ):
        raise ValueError("invalid checkpoint manifest")
    permitted = re.compile(
        r"(?:queue\.sqlite3|artifacts\.sqlite3|"
        r"catalogs/tenant-[a-z0-9][a-z0-9_-]{0,63}\.sqlite3|"
        r"objects/v1/tenant-[a-z0-9][a-z0-9_-]{0,63}/[a-f0-9]{64}\.zip)"
    )
    for name, entry in value["files"].items():
        if (
            not permitted.fullmatch(name)
            or not isinstance(entry, dict)
            or set(entry) != {"size", "sha256"}
        ):
            raise ValueError("invalid checkpoint member")
        path = root / name
        if (
            path.is_symlink()
            or any(p.is_symlink() for p in path.parents if p != root.parent)
            or type(entry["size"]) is not int
            or not 0 < entry["size"] <= 512 * 1024 * 1024
            or path.stat().st_size != entry["size"]
            or sha(path) != entry["sha256"]
        ):
            raise ValueError("checkpoint member failed verification")
    members = list(root.rglob("*"))
    if root.is_symlink() or any(p.is_symlink() for p in members):
        raise ValueError("checkpoint links are forbidden")
    actual = {p.relative_to(root).as_posix() for p in members if p.is_file()}
    if actual != set(value["files"]) | {"manifest.json"}:
        raise ValueError("unexpected checkpoint member")
    for name in value["files"]:
        if name.endswith(".sqlite3"):
            with readonly(root / name) as db:
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("corrupt checkpoint database")
    objects, references, jobs = inventory(root)
    if (jobs, len(objects), len(references)) != (
        value["jobs"],
        value["artifacts"],
        value["references"],
    ):
        raise ValueError("checkpoint inventory mismatch")
    for (tenant, digest), size in objects.items():
        if digest_file(root / "objects" / key(tenant, digest)) != (digest, size):
            raise ValueError("missing or corrupt referenced bytes")
    return value


def restore(source: Path, target: Path):
    if target.exists():
        raise FileExistsError("restore target exists")
    started = time.monotonic()
    source_manifest = verify(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        staged = Path(temporary) / "restored"
        staged.mkdir()
        (staged / "catalogs").mkdir()
        (staged / "objects").mkdir()
        for name, entry in source_manifest["files"].items():
            destination = staged / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with (source / name).open("rb") as src, destination.open("xb") as dst:
                remaining = entry["size"]
                while remaining:
                    chunk = src.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("checkpoint changed during restore")
                    dst.write(chunk)
                    remaining -= len(chunk)
                if src.read(1):
                    raise ValueError("checkpoint changed during restore")
                dst.flush()
                os.fsync(dst.fileno())
        (staged / "manifest.json").write_text(canonical(source_manifest), encoding="utf-8")
        manifest = verify(staged)  # Validate the exact copied bytes before exposing state.
        with closing(sqlite3.connect(staged / "queue.sqlite3")) as db:
            db.execute("DELETE FROM suite_workers")  # No source worker is alive in a fresh restore.
            db.commit()
        # Fixed runtime layout matches the API's SIMWEAVE_DB-derived sibling paths.
        os.rename(staged / "queue.sqlite3", staged / "runs.sqlite3.suites")
        os.rename(staged / "artifacts.sqlite3", staged / "runs.sqlite3.suites.artifacts")
        os.rename(staged / "catalogs", staged / "runs.sqlite3.catalogs")
        os.rename(staged / "objects", staged / "runs.sqlite3.suites.objects")
        (staged / "manifest.json").unlink()
        if target.exists():
            raise FileExistsError("restore target exists")
        os.rename(staged, target)
    return {
        "schema_version": 1,
        "jobs": manifest["jobs"],
        "artifacts": manifest["artifacts"],
        "references": manifest["references"],
        "seconds": round(time.monotonic() - started, 3),
    }
