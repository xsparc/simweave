"""Immutable, tenant-scoped verified bundles; no deletion or ambient credentials."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

from simweave.bundles import MAX_TOTAL as MAX_BUNDLE
from simweave.bundles import read_bundle
from simweave.observability import counted
from simweave.store import Capacity, Store


def key(tenant: str, digest: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", tenant):
        raise ValueError("invalid tenant")
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("invalid artifact digest")
    return f"v1/tenant-{tenant}/{digest}.zip"


def digest_file(path: Path) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BUNDLE:
                raise ValueError("artifact exceeds bundle limit")
            digest.update(chunk)
    return digest.hexdigest(), size


def publish(staged: Path, target: Path):
    os.link(staged, target)
    if os.name == "posix":
        descriptor = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def backup_database(store: Store, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        staged = Path(temporary) / "metadata.sqlite3"
        with store.connect() as source, closing(sqlite3.connect(staged)) as destination:
            source.backup(destination)
            destination.execute("PRAGMA journal_mode=DELETE")
        publish(staged, target)


class Filesystem:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, source: Path):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
            staged = Path(temporary) / "object"
            with source.open("rb") as src, staged.open("xb") as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())
            try:
                publish(staged, target)
            except FileExistsError:
                pass
        # Existing objects must be identical, including after interrupted publication.
        if digest_file(target) != digest_file(source):
            raise ValueError("existing object differs")

    def get(self, name: str, target: Path):
        with (self.root / name).open("rb") as src, target.open("xb") as dst:
            size = 0
            while chunk := src.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BUNDLE:
                    raise ValueError("artifact exceeds bundle limit")
                dst.write(chunk)


class S3:
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        region: str,
        access_key: str,
        secret: str,
        ca_bundle: str | None = None,
    ):
        from boto3.session import Session
        from botocore.config import Config

        url = urlsplit(endpoint)
        if (
            not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
            or (
                url.scheme != "https"
                and not (url.scheme == "http" and url.hostname in ("127.0.0.1", "::1"))
            )
            or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket)
            or not access_key
            or not secret
        ):
            raise ValueError("invalid explicit S3 configuration")
        self.bucket = bucket
        self.client = Session(
            aws_access_key_id=access_key, aws_secret_access_key=secret, region_name=region
        ).client(
            "s3",
            endpoint_url=endpoint,
            verify=ca_bundle if ca_bundle else True,
            config=Config(
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 2},
                proxies={},
                s3={"addressing_style": "path"},
            ),
        )

    def put(self, name: str, source: Path):
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            with source.open("rb") as stream:
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=name,
                    Body=stream,
                    IfNoneMatch="*",
                    ContentType="application/zip",
                )
        except ClientError as exc:
            if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 412:
                raise RuntimeError("S3 publication failed") from None
        except BotoCoreError:
            raise RuntimeError("S3 publication failed") from None
        # Never trust ETag (multipart/encryption change its meaning).
        with tempfile.TemporaryDirectory() as temporary:
            check = Path(temporary) / "check"
            self.get(name, check)
            if digest_file(check) != digest_file(source):
                raise ValueError("existing object differs")

    def get(self, name: str, target: Path):
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            response = self.client.get_object(Bucket=self.bucket, Key=name)
        except (BotoCoreError, ClientError):
            raise RuntimeError("S3 retrieval failed") from None
        body = response["Body"]
        try:
            if response["ContentLength"] > MAX_BUNDLE:
                raise ValueError("artifact exceeds bundle limit")
            size = 0
            with target.open("xb") as stream:
                while chunk := body.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_BUNDLE:
                        raise ValueError("artifact exceeds bundle limit")
                    stream.write(chunk)
        except BotoCoreError:
            raise RuntimeError("S3 retrieval failed") from None
        finally:
            body.close()


class Artifacts:
    def __init__(self, database: Path, backend):
        self.db = Store(database)
        self.backend = backend
        self.scratch = database.parent
        with self.db.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS operation_counters "
                "(name TEXT PRIMARY KEY, value INTEGER NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS artifacts (tenant TEXT, digest TEXT, "
                "size INTEGER NOT NULL, PRIMARY KEY(tenant,digest))"
            )

    @counted("artifact_put")
    def put(self, tenant: str, source: Path) -> str:
        key(tenant, "0" * 64)
        # Snapshot before verification; publish precisely the verified bytes.
        with tempfile.TemporaryDirectory(dir=self.scratch) as temporary:
            staged = Path(temporary) / "bundle.zip"
            Filesystem(source.parent).get(source.name, staged)
            read_bundle(staged)
            digest, size = digest_file(staged)
            name = key(tenant, digest)
            self.check_capacity(tenant, digest)
            # Slow object I/O stays outside metadata transactions.
            self.backend.put(name, staged)
            self.retain(tenant, digest, size)
            return digest

    @counted("artifact_get")
    def get(self, tenant: str, digest: str, target: Path):
        name = key(tenant, digest)
        size = self.size(tenant, digest)
        if size is None:
            raise KeyError("artifact not found")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
            staged = Path(temporary) / "bundle.zip"
            self.backend.get(name, staged)
            if digest_file(staged) != (digest, size):
                raise ValueError("artifact integrity failure")
            publish(staged, target)

    def recover(self, tenant: str, destination) -> int:
        key(tenant, "0" * 64)
        with self.db.connect() as db:
            rows = db.execute(
                "SELECT digest FROM artifacts WHERE tenant=? ORDER BY digest", (tenant,)
            ).fetchall()
        for row in rows:
            with tempfile.TemporaryDirectory(dir=self.scratch) as temporary:
                staged = Path(temporary) / "bundle.zip"
                self.get(tenant, row[0], staged)
                destination.put(key(tenant, row[0]), staged)
        return len(rows)

    def backup(self, target: Path):
        backup_database(self.db, target)

    def check_capacity(self, tenant, digest):
        with self.db.connect() as db:
            if (
                db.execute("SELECT count(*) FROM artifacts WHERE tenant=?", (tenant,)).fetchone()[0]
                >= 10000
                and not db.execute(
                    "SELECT 1 FROM artifacts WHERE tenant=? AND digest=?", (tenant, digest)
                ).fetchone()
            ):
                raise Capacity("artifact retention capacity reached")

    def retain(self, tenant, digest, size):
        with self.db.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT size FROM artifacts WHERE tenant=? AND digest=?", (tenant, digest)
            ).fetchone()
            if (
                not existing
                and db.execute(
                    "SELECT count(*) FROM artifacts WHERE tenant=?", (tenant,)
                ).fetchone()[0]
                >= 10000
            ):
                raise Capacity("artifact retention capacity reached")
            db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?)", (tenant, digest, size))

    def size(self, tenant, digest):
        with self.db.connect() as db:
            row = db.execute(
                "SELECT size FROM artifacts WHERE tenant=? AND digest=?", (tenant, digest)
            ).fetchone()
            return row[0] if row else None

    def count_operation(self, name):
        try:
            with self.db.connect() as db:
                db.execute(
                    "INSERT INTO operation_counters VALUES(?,1) ON CONFLICT(name) DO "
                    "UPDATE SET value=value+1",
                    (name,),
                )
        except sqlite3.Error:
            pass
