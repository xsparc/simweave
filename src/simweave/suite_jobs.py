"""Single-host durable suite scheduling with fenced attempts and explicit recovery."""

from __future__ import annotations

import re
import tempfile
import threading
import time
import uuid
from pathlib import Path

from simweave.artifacts import Artifacts, key
from simweave.store import Capacity, Conflict, LostClaim, Store
from simweave.suites import Suite, SuiteInterrupted, execute_suite, review


class SuiteJobs:
    lease_seconds = 30

    def __init__(self, path: Path):
        self.db = Store(path)
        with self.db.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS suite_jobs_v1 (
                    id TEXT PRIMARY KEY, tenant TEXT NOT NULL, request_key TEXT NOT NULL,
                    suite TEXT NOT NULL, digest TEXT NOT NULL, status TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0, claim TEXT, lease REAL,
                    created REAL NOT NULL, updated REAL NOT NULL,
                    artifact TEXT, exit_code INTEGER, error TEXT,
                    UNIQUE(tenant,request_key)
                );
                CREATE INDEX IF NOT EXISTS suite_queue ON suite_jobs_v1(status,created,id);
                CREATE INDEX IF NOT EXISTS suite_tenant ON suite_jobs_v1(tenant,created,id);
                CREATE TABLE IF NOT EXISTS suite_workers (
                    id TEXT PRIMARY KEY, updated REAL NOT NULL, state TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS suite_counters (
                    name TEXT PRIMARY KEY, value INTEGER NOT NULL
                );
            """)

    def worker_ping(self, worker, state):
        now = time.time()
        with self.db.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM suite_workers WHERE updated<?", (now - 3600,))
            if db.execute("SELECT count(*) FROM suite_workers").fetchone()[0] >= 1024:
                db.execute(
                    "DELETE FROM suite_workers WHERE id IN "
                    "(SELECT id FROM suite_workers ORDER BY updated LIMIT 1)"
                )
            db.execute(
                "INSERT INTO suite_workers VALUES(?,?,?) ON CONFLICT(id) "
                "DO UPDATE SET updated=excluded.updated,state=excluded.state",
                (worker, now, state),
            )

    @staticmethod
    def public(row):
        return {
            "schema_version": 1,
            **{
                name: row[name]
                for name in (
                    "id",
                    "status",
                    "attempt",
                    "created",
                    "updated",
                    "artifact",
                    "exit_code",
                    "error",
                )
            },
            "suite_digest": row["digest"],
        }

    def submit(self, tenant: str, suite: Suite, request_key: str):
        key(tenant, "0" * 64)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_key):
            raise ValueError("invalid idempotency key")
        payload = suite.model_dump_json()
        if len(payload.encode()) > 65536:
            raise ValueError("suite exceeds 64 KiB")
        with self.db.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM suite_jobs_v1 WHERE tenant=? AND request_key=?",
                (tenant, request_key),
            ).fetchone()
            if row:
                if row["digest"] != suite.digest():
                    raise Conflict("idempotency key belongs to another suite")
                return self.public(row)
            if (
                db.execute(
                    "SELECT COUNT(*) FROM suite_jobs_v1 WHERE tenant=?", (tenant,)
                ).fetchone()[0]
                >= 1000
            ):
                raise Capacity("suite retention capacity reached")
            if (
                db.execute(
                    "SELECT COUNT(*) FROM suite_jobs_v1 WHERE status IN ('queued','running')"
                ).fetchone()[0]
                >= 1000
            ):
                raise Capacity("suite queue capacity reached")
            identifier, now = uuid.uuid4().hex, time.time()
            db.execute(
                "INSERT INTO suite_jobs_v1(id,tenant,request_key,suite,digest,status,"
                "created,updated) VALUES(?,?,?,?,?,'queued',?,?)",
                (identifier, tenant, request_key, payload, suite.digest(), now, now),
            )
            return self.public(
                db.execute("SELECT * FROM suite_jobs_v1 WHERE id=?", (identifier,)).fetchone()
            )

    def get(self, tenant: str, identifier: str):
        with self.db.connect() as db:
            row = db.execute(
                "SELECT * FROM suite_jobs_v1 WHERE tenant=? AND id=?", (tenant, identifier)
            ).fetchone()
            return self.public(row) if row else None

    def list(self, tenant: str, after: str = "", limit: int = 50):
        if not 1 <= limit <= 100:
            raise ValueError("invalid page size")
        with self.db.connect() as db:
            return [
                self.public(row)
                for row in db.execute(
                    "SELECT * FROM suite_jobs_v1 WHERE tenant=? AND id>? ORDER BY id LIMIT ?",
                    (tenant, after, limit),
                )
            ]

    def expire(self):
        now = time.time()
        with self.db.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "UPDATE suite_jobs_v1 SET status='failed',error='worker_lost',"
                "updated=? WHERE status='running' AND lease<=?",
                (now, now),
            ).rowcount
            db.execute(
                "INSERT INTO suite_counters VALUES('lease_losses',?) "
                "ON CONFLICT(name) DO UPDATE SET value=value+excluded.value",
                (count,),
            )
            return count

    def claim(self):
        self.expire()
        now, claim = time.time(), uuid.uuid4().hex
        with self.db.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM suite_jobs_v1 WHERE status='queued' ORDER BY created,id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            db.execute(
                "UPDATE suite_jobs_v1 SET status='running',attempt=attempt+1,claim=?,"
                "lease=?,updated=? WHERE id=?",
                (claim, now + self.lease_seconds, now, row["id"]),
            )
            return {
                "id": row["id"],
                "tenant": row["tenant"],
                "claim": claim,
                "suite": Suite.model_validate_json(row["suite"]),
            }

    def heartbeat(self, identifier: str, claim: str):
        now = time.time()
        with self.db.connect() as db:
            changed = db.execute(
                "UPDATE suite_jobs_v1 SET lease=?,updated=? WHERE id=? "
                "AND claim=? AND status='running' AND lease>?",
                (now + self.lease_seconds, now, identifier, claim, now),
            ).rowcount
            if not changed:
                raise LostClaim()

    def finish(self, identifier: str, claim: str, artifact=None, exit_code=None, error=None):
        now = time.time()
        with self.db.connect() as db:
            changed = db.execute(
                "UPDATE suite_jobs_v1 SET status=?,artifact=?,exit_code=?,"
                "error=?,updated=? WHERE id=? AND claim=? "
                "AND status='running' AND lease>?",
                (
                    "failed" if error else "succeeded",
                    artifact,
                    exit_code,
                    error,
                    now,
                    identifier,
                    claim,
                    now,
                ),
            ).rowcount
            return bool(changed)

    def cancel(self, tenant: str, identifier: str):
        with self.db.connect() as db:
            db.execute(
                "UPDATE suite_jobs_v1 SET status='cancelled',updated=? WHERE tenant=? "
                "AND id=? AND status IN ('queued','running')",
                (time.time(), tenant, identifier),
            )
        return self.get(tenant, identifier)

    def retry(self, tenant: str, identifier: str):
        self.expire()
        with self.db.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM suite_jobs_v1 WHERE tenant=? AND id=?", (tenant, identifier)
            ).fetchone()
            if row is None:
                return None
            if row["status"] != "failed" or row["attempt"] >= 5:
                raise Conflict("only failed jobs below five attempts may be retried")
            if (
                db.execute(
                    "SELECT COUNT(*) FROM suite_jobs_v1 WHERE status IN ('queued','running')"
                ).fetchone()[0]
                >= 1000
            ):
                raise Capacity("suite queue capacity reached")
            db.execute(
                "UPDATE suite_jobs_v1 SET status='queued',claim=NULL,lease=NULL,"
                "artifact=NULL,exit_code=NULL,error=NULL,updated=? WHERE id=?",
                (time.time(), identifier),
            )
        return self.get(tenant, identifier)


def work_once(jobs: SuiteJobs, artifacts: Artifacts, worker_id=None) -> bool:
    worker = worker_id or uuid.uuid4().hex
    jobs.worker_ping(worker, "idle")
    try:
        return _work_once(jobs, artifacts, worker)
    finally:
        jobs.worker_ping(worker, "idle" if worker_id else "offline")


def _work_once(jobs: SuiteJobs, artifacts: Artifacts, worker) -> bool:
    job = jobs.claim()
    if job is None:
        return False
    last = 0.0

    def checkpoint():
        nonlocal last
        if time.monotonic() - last >= 0.25:
            try:
                jobs.heartbeat(job["id"], job["claim"])
                jobs.worker_ping(worker, "busy")
            except LostClaim:
                raise SuiteInterrupted() from None
            last = time.monotonic()

    try:
        with tempfile.TemporaryDirectory(dir=jobs.db.path.parent) as temporary:
            output = Path(temporary) / "suite"
            report = execute_suite(job["suite"], output, checkpoint=checkpoint)
            jobs.heartbeat(job["id"], job["claim"])
            stopped = threading.Event()

            def renew_publication():
                # Large bundle verification/uploads can exceed one lease. Bound renewal
                # to five minutes; a stuck backend still loses authority eventually.
                deadline = time.monotonic() + 300
                while not stopped.wait(1) and time.monotonic() < deadline:
                    try:
                        jobs.heartbeat(job["id"], job["claim"])
                        jobs.worker_ping(worker, "busy")
                    except Exception:
                        return  # Failure is fenced by finish(), never a stale success.

            renewal = threading.Thread(target=renew_publication, daemon=True)
            renewal.start()
            try:
                digest = artifacts.put(job["tenant"], output / "evidence.zip")
            finally:
                stopped.set()
                renewal.join(timeout=6)
            jobs.finish(job["id"], job["claim"], digest, review(report).exit_code)
    except (SuiteInterrupted, LostClaim):
        pass
    except Exception:
        jobs.finish(job["id"], job["claim"], error="execution_or_storage_failed")
    return True


def work_forever(jobs: SuiteJobs, artifacts: Artifacts):
    worker = uuid.uuid4().hex
    try:
        while True:
            if not work_once(jobs, artifacts, worker):
                time.sleep(0.5)
    except KeyboardInterrupt:
        return
    finally:
        jobs.worker_ping(worker, "offline")
