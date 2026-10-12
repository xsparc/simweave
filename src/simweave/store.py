"""Single-host SQLite run repository with durable, leased worker claims."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from simweave.contracts import RunResult, Sample, Scenario, canonical


class Conflict(Exception):
    pass


class Capacity(Exception):
    pass


class LostClaim(Exception):
    pass


class Store:
    lease_seconds = 30

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported database schema version")
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, tenant TEXT NOT NULL, idempotency_key TEXT,
                    scenario TEXT NOT NULL, digest TEXT NOT NULL, status TEXT NOT NULL,
                    created REAL NOT NULL, updated REAL NOT NULL,
                    worker TEXT, lease_until REAL, result TEXT, error TEXT,
                    UNIQUE(tenant, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS runs_tenant ON runs(tenant, created DESC, id DESC);
                CREATE INDEX IF NOT EXISTS runs_queue ON runs(status, created);
                CREATE TABLE IF NOT EXISTS samples (
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    step INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(run_id, step)
                );
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def public(row) -> dict:
        return {
            "id": row["id"],
            "scenario": json.loads(row["scenario"]),
            "scenario_digest": row["digest"],
            "status": row["status"],
            "created_at": row["created"],
            "updated_at": row["updated"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "error": row["error"],
        }

    def submit(self, tenant: str, scenario: Scenario, key: str | None = None) -> tuple[dict, bool]:
        digest, now = scenario.digest(), time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if key:
                row = db.execute(
                    "SELECT * FROM runs WHERE tenant=? AND idempotency_key=?", (tenant, key)
                ).fetchone()
                if row:
                    if row["digest"] != digest:
                        raise Conflict("idempotency key already used for another scenario")
                    return self.public(row), False
            active = db.execute(
                "SELECT COUNT(*) FROM runs WHERE tenant=? AND status IN ('queued','running')",
                (tenant,),
            ).fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM runs WHERE tenant=?", (tenant,)).fetchone()[0]
            global_active = db.execute(
                "SELECT COUNT(*) FROM runs WHERE status IN ('queued','running')"
            ).fetchone()[0]
            if active >= 20 or total >= 1000 or global_active >= 64:
                raise Capacity("run capacity reached; finish or delete existing runs")
            identifier = uuid.uuid4().hex
            db.execute(
                "INSERT INTO runs(id,tenant,idempotency_key,scenario,digest,status,"
                "created,updated) "
                "VALUES(?,?,?,?,?,'queued',?,?)",
                (identifier, tenant, key, canonical(scenario.model_dump()), digest, now, now),
            )
            return self.public(
                db.execute("SELECT * FROM runs WHERE id=?", (identifier,)).fetchone()
            ), True

    def get(self, tenant: str, identifier: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM runs WHERE id=? AND tenant=?", (identifier, tenant)
            ).fetchone()
            return self.public(row) if row else None

    def list(self, tenant: str, limit: int = 30, before: str | None = None) -> list[dict]:
        with self.connect() as db:
            boundary = (
                db.execute(
                    "SELECT created,id FROM runs WHERE tenant=? AND id=?", (tenant, before)
                ).fetchone()
                if before
                else None
            )
            if before and not boundary:
                raise ValueError("unknown pagination cursor")
            if boundary:
                rows = db.execute(
                    "SELECT * FROM runs WHERE tenant=? AND (created,id)<(?,?) "
                    "ORDER BY created DESC,id DESC LIMIT ?",
                    (tenant, boundary[0], boundary[1], limit),
                )
            else:
                rows = db.execute(
                    "SELECT * FROM runs WHERE tenant=? ORDER BY created DESC,id DESC LIMIT ?",
                    (tenant, limit),
                )
            return [self.public(row) for row in rows]

    def cancel(self, tenant: str, identifier: str) -> dict | None:
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET status='cancelled',updated=? WHERE tenant=? AND id=? "
                "AND status IN ('queued','running')",
                (time.time(), tenant, identifier),
            )
        return self.get(tenant, identifier)

    def delete(self, tenant: str, identifier: str) -> bool:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT status FROM runs WHERE tenant=? AND id=?", (tenant, identifier)
            ).fetchone()
            if not row:
                return False
            if row[0] in ("queued", "running"):
                raise Conflict("cancel or finish a run before deleting it")
            db.execute("DELETE FROM runs WHERE tenant=? AND id=?", (tenant, identifier))
            return True

    def claim(self, worker: str) -> dict | None:
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE runs SET status='failed',error='worker_lost',updated=? "
                "WHERE status='running' AND lease_until<=?",
                (now, now),
            )
            row = db.execute(
                "SELECT * FROM runs WHERE status='queued' ORDER BY created,id LIMIT 1"
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE runs SET status='running',worker=?,lease_until=?,updated=? WHERE id=?",
                (worker, now + self.lease_seconds, now, row["id"]),
            )
            return {"id": row["id"], "scenario": Scenario.model_validate_json(row["scenario"])}

    def append(self, identifier: str, worker: str, samples: list[Sample]) -> None:
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            updated = db.execute(
                "UPDATE runs SET lease_until=?,updated=? WHERE id=? AND worker=? "
                "AND status='running' AND lease_until>?",
                (now + self.lease_seconds, now, identifier, worker, now),
            )
            if not updated.rowcount:
                raise LostClaim()
            db.executemany(
                "INSERT INTO samples(run_id,step,payload) VALUES(?,?,?)",
                [(identifier, s.step, canonical(s.model_dump())) for s in samples],
            )

    def finish(
        self, identifier: str, worker: str, result: RunResult | None, error: str | None = None
    ) -> bool:
        now = time.time()
        with self.connect() as db:
            updated = db.execute(
                "UPDATE runs SET status=?,result=?,error=?,updated=? WHERE id=? AND worker=? "
                "AND status='running' AND lease_until>?",
                (
                    "succeeded" if result else "failed",
                    result.model_dump_json() if result else None,
                    error,
                    now,
                    identifier,
                    worker,
                    now,
                ),
            )
            return bool(updated.rowcount)

    def samples(
        self, tenant: str, identifier: str, after: int = -1, limit: int = 1000
    ) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT s.payload FROM samples s JOIN runs r ON r.id=s.run_id "
                "WHERE r.tenant=? AND r.id=? AND s.step>? ORDER BY s.step LIMIT ?",
                (tenant, identifier, after, limit),
            )
            return [json.loads(row[0]) for row in rows]

    def iter_samples(self, tenant: str, identifier: str):
        after = -1
        while batch := self.samples(tenant, identifier, after):
            yield from batch
            after = batch[-1]["step"]
