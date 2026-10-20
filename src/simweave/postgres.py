"""Optional PostgreSQL suite boundary. SQL is explicit; no SQLite emulation."""

import os
import re
import uuid
from contextlib import contextmanager

from simweave.artifacts import S3, Artifacts, key
from simweave.store import Capacity, Conflict, LostClaim
from simweave.suite_jobs import SuiteJobs
from simweave.suites import Suite

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER
NOT NULL);
INSERT INTO schema_version VALUES(1,1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS admission (id INTEGER PRIMARY KEY CHECK(id=1), paused BOOLEAN NOT NULL);
INSERT INTO admission VALUES(1,false) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS suite_jobs_v1 (
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, request_key TEXT NOT NULL,
 suite TEXT NOT NULL, digest TEXT NOT NULL, status TEXT NOT NULL,
 attempt INTEGER NOT NULL DEFAULT 0, claim TEXT, lease DOUBLE PRECISION,
 created DOUBLE PRECISION NOT NULL, updated DOUBLE PRECISION NOT NULL,
 artifact TEXT, exit_code INTEGER, error TEXT, UNIQUE(tenant,request_key));
CREATE INDEX IF NOT EXISTS suite_queue ON suite_jobs_v1(status,created,id);
CREATE INDEX IF NOT EXISTS suite_tenant ON suite_jobs_v1(tenant,id);
CREATE TABLE IF NOT EXISTS suite_workers (id TEXT PRIMARY KEY, updated DOUBLE PRECISION NOT
NULL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS suite_counters (name TEXT PRIMARY KEY, value BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS artifacts (tenant TEXT NOT NULL, digest TEXT NOT NULL, size BIGINT
NOT NULL, PRIMARY KEY(tenant,digest));
CREATE TABLE IF NOT EXISTS operation_counters (name TEXT PRIMARY KEY, value BIGINT NOT NULL);
"""
NOW = "extract(epoch from clock_timestamp())::double precision"


def value(db, sql, args=()):
    return db.execute(sql, args).fetchone()["v"]


class Unavailable(RuntimeError):
    """Sanitized storage-boundary failure, safe to map to HTTP 503."""


class Database:
    def __init__(self, scratch, *, initialize=False):
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self.scratch = scratch
        scratch.mkdir(parents=True, exist_ok=True)
        dsn = os.environ.get("SIMWEAVE_POSTGRES_DSN")
        if not dsn:
            raise ValueError("SIMWEAVE_POSTGRES_DSN is required")
        options = {
            "row_factory": dict_row,
            "connect_timeout": 5,
            "options": (
                "-c statement_timeout=10000 -c lock_timeout=5000 -c search_path=simweave,pg_catalog"
            ),
        }
        # Admission holders have a separate bounded pool, avoiding nested-pool starvation.
        self.pool = ConnectionPool(
            dsn, min_size=0, max_size=16, timeout=5, kwargs=options, open=True
        )
        self.gates = ConnectionPool(
            dsn, min_size=0, max_size=16, timeout=5, kwargs=options, open=True
        )
        try:
            with self.connection() as db:
                if initialize:
                    db.execute("SELECT pg_advisory_xact_lock(191910)")
                    db.execute("CREATE SCHEMA IF NOT EXISTS simweave")
                    db.execute(SCHEMA)
                if value(db, "SELECT version AS v FROM schema_version WHERE id=1") != 1:
                    raise ValueError("unsupported PostgreSQL schema")
        except Exception:
            self.close()
            raise Unavailable("PostgreSQL unavailable or schema not initialized") from None

    @contextmanager
    def connection(self, gate=False):
        import psycopg
        from psycopg_pool import PoolTimeout

        try:
            with (self.gates if gate else self.pool).connection() as db:
                yield db
        except (psycopg.Error, PoolTimeout):
            raise Unavailable("PostgreSQL operation unavailable") from None

    def close(self):
        self.gates.close()
        self.pool.close()


class Gate:
    def __init__(self, database):
        self.database = database

    @contextmanager
    def hold(self, paused=False):
        with self.database.connection(gate=True) as db:
            db.execute("SELECT pg_advisory_xact_lock_shared(191911)")
            if value(db, "SELECT paused AS v FROM admission WHERE id=1") != paused:
                raise Conflict("maintenance admission state does not permit this operation")
            yield

    def paused(self):
        with self.database.connection() as db:
            return value(db, "SELECT paused AS v FROM admission WHERE id=1")

    def set(self, paused):
        with self.database.connection() as db:
            db.execute("SELECT pg_advisory_xact_lock(191911)")
            db.execute("UPDATE admission SET paused=%s WHERE id=1", (paused,))
        return {"schema_version": 1, "paused": paused}


class Jobs:
    lease_seconds = 30
    public = staticmethod(SuiteJobs.public)

    def __init__(self, database):
        self.database = database
        self.scratch = database.scratch
        self.gate = Gate(database)

    def submit(self, tenant, suite, request_key):
        key(tenant, "0" * 64)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_key):
            raise ValueError("invalid idempotency key")
        payload = suite.model_dump_json()
        if len(payload.encode()) > 65536:
            raise ValueError("suite exceeds 64 KiB")
        with self.gate.hold(), self.database.connection() as db:
            db.execute("SELECT pg_advisory_xact_lock(191912)")
            row = db.execute(
                "SELECT * FROM suite_jobs_v1 WHERE tenant=%s AND request_key=%s",
                (tenant, request_key),
            ).fetchone()
            if row:
                if row["digest"] != suite.digest():
                    raise Conflict("idempotency key belongs to another suite")
                return self.public(row)
            if (
                value(db, "SELECT count(*) AS v FROM suite_jobs_v1 WHERE tenant=%s", (tenant,))
                >= 1000
            ):
                raise Capacity("suite retention capacity reached")
            self.capacity(db)
            return self.public(
                db.execute(
                    f"INSERT INTO "
                    f"suite_jobs_v1(id,tenant,request_key,suite,digest,status,created,updated) "
                    f"VALUES(%s,%s,%s,%s,%s,'queued',{NOW},{NOW}) RETURNING *",
                    (uuid.uuid4().hex, tenant, request_key, payload, suite.digest()),
                ).fetchone()
            )

    @staticmethod
    def capacity(db):
        if (
            value(
                db, "SELECT count(*) AS v FROM suite_jobs_v1 WHERE status IN ('queued','running')"
            )
            >= 1000
        ):
            raise Capacity("suite queue capacity reached")

    def get(self, tenant, identifier):
        with self.database.connection() as db:
            row = db.execute(
                "SELECT * FROM suite_jobs_v1 WHERE tenant=%s AND id=%s", (tenant, identifier)
            ).fetchone()
            return self.public(row) if row else None

    def list(self, tenant, after="", limit=50):
        if not 1 <= limit <= 100:
            raise ValueError("invalid page size")
        with self.database.connection() as db:
            return [
                self.public(r)
                for r in db.execute(
                    "SELECT * FROM suite_jobs_v1 WHERE tenant=%s AND id>%s ORDER BY id LIMIT %s",
                    (tenant, after, limit),
                )
            ]

    def expire(self):
        with self.database.connection() as db:
            count = db.execute(
                f"UPDATE suite_jobs_v1 SET "
                f"status='failed',error='worker_lost',updated={NOW} WHERE "
                f"status='running' AND lease<={NOW}"
            ).rowcount
            if count:
                db.execute(
                    "INSERT INTO suite_counters VALUES('lease_losses',%s) ON "
                    "CONFLICT(name) DO UPDATE SET "
                    "value=suite_counters.value+excluded.value",
                    (count,),
                )
            return count

    @staticmethod
    def worker_record(db, worker, state):
        db.execute("SELECT pg_advisory_xact_lock(191913)")
        db.execute(f"DELETE FROM suite_workers WHERE updated<{NOW}-3600 AND state!='busy'")
        if not db.execute("SELECT 1 FROM suite_workers WHERE id=%s", (worker,)).fetchone():
            if value(db, "SELECT count(*) AS v FROM suite_workers") >= 1024:
                db.execute(
                    "DELETE FROM suite_workers WHERE id IN (SELECT id FROM "
                    "suite_workers WHERE state!='busy' ORDER BY updated LIMIT 1)"
                )
            if value(db, "SELECT count(*) AS v FROM suite_workers") >= 1024:
                raise Capacity("worker presence capacity reached")
        db.execute(
            f"INSERT INTO suite_workers VALUES(%s,{NOW},%s) ON CONFLICT(id) DO "
            f"UPDATE SET updated=excluded.updated,state=excluded.state",
            (worker, state),
        )

    def worker_ping(self, worker, state):
        with self.database.connection() as db:
            self.worker_record(db, worker, state)

    def claim(self, worker=None):
        self.expire()
        try:
            with self.gate.hold(), self.database.connection() as db:
                row = db.execute(
                    "SELECT * FROM suite_jobs_v1 WHERE status='queued' ORDER BY "
                    "created,id LIMIT 1 FOR UPDATE SKIP LOCKED"
                ).fetchone()
                if row is None:
                    return None
                claim = uuid.uuid4().hex
                db.execute(
                    f"UPDATE suite_jobs_v1 SET "
                    f"status='running',attempt=attempt+1,claim=%s,lease={NOW}+%s,updated={NOW} "
                    f"WHERE id=%s",
                    (claim, self.lease_seconds, row["id"]),
                )
                if worker:
                    self.worker_record(db, worker, "busy")
                return {
                    "id": row["id"],
                    "tenant": row["tenant"],
                    "claim": claim,
                    "suite": Suite.model_validate_json(row["suite"]),
                }
        except Conflict:
            return None

    def heartbeat(self, identifier, claim):
        with self.database.connection() as db:
            if not db.execute(
                f"UPDATE suite_jobs_v1 SET lease={NOW}+%s,updated={NOW} WHERE "
                f"id=%s AND claim=%s AND status='running' AND lease>{NOW}",
                (self.lease_seconds, identifier, claim),
            ).rowcount:
                raise LostClaim()

    def finish(self, identifier, claim, artifact=None, exit_code=None, error=None):
        with self.database.connection() as db:
            return bool(
                db.execute(
                    f"UPDATE suite_jobs_v1 SET "
                    f"status=%s,artifact=%s,exit_code=%s,error=%s,updated={NOW} "
                    f"WHERE id=%s AND claim=%s AND status='running' AND "
                    f"lease>{NOW}",
                    (
                        "failed" if error else "succeeded",
                        artifact,
                        exit_code,
                        error,
                        identifier,
                        claim,
                    ),
                ).rowcount
            )

    def cancel(self, tenant, identifier):
        with self.database.connection() as db:
            db.execute(
                f"UPDATE suite_jobs_v1 SET status='cancelled',updated={NOW} WHERE "
                f"tenant=%s AND id=%s AND status IN ('queued','running')",
                (tenant, identifier),
            )
        return self.get(tenant, identifier)

    def retry(self, tenant, identifier):
        self.expire()
        with self.gate.hold(), self.database.connection() as db:
            db.execute("SELECT pg_advisory_xact_lock(191912)")
            row = db.execute(
                "SELECT * FROM suite_jobs_v1 WHERE tenant=%s AND id=%s FOR UPDATE",
                (tenant, identifier),
            ).fetchone()
            if row is None:
                return None
            if row["status"] != "failed" or row["attempt"] >= 5:
                raise Conflict("only failed jobs below five attempts may be retried")
            self.capacity(db)
            row = db.execute(
                f"UPDATE suite_jobs_v1 SET "
                "status='queued',claim=NULL,lease=NULL,artifact=NULL,"
                f"exit_code=NULL,error=NULL,updated={NOW} "
                f"WHERE id=%s RETURNING *",
                (identifier,),
            ).fetchone()
            return self.public(row)

    def activity(self):
        with self.database.connection() as db:
            return (
                value(db, "SELECT count(*) AS v FROM suite_jobs_v1 WHERE status='running'"),
                value(db, "SELECT count(*) AS v FROM suite_workers WHERE state='busy'"),
            )

    def acknowledge_stopped(self):
        self.expire()
        with self.database.connection() as db:
            if value(db, "SELECT count(*) AS v FROM suite_jobs_v1 WHERE status='running'"):
                raise Conflict("wait for outstanding leases to expire")
            return db.execute("DELETE FROM suite_workers").rowcount

    def metrics(self, artifacts, tenant=None):
        where, args = ("WHERE tenant=%s", (tenant,)) if tenant else ("", ())
        conjunction = "AND" if tenant else "WHERE"
        with self.database.connection() as db:
            counts = {
                r["status"]: r["v"]
                for r in db.execute(
                    f"SELECT status,count(*) AS v FROM suite_jobs_v1 {where} GROUP BY status", args
                )
            }
            age = value(
                db,
                f"SELECT coalesce(greatest(0,{NOW}-min(created)),0) AS v FROM "
                f"suite_jobs_v1 {where} {conjunction} status='queued'",
                args,
            )
            lost = value(
                db,
                f"SELECT count(*) AS v FROM suite_jobs_v1 {where} {conjunction} "
                f"error='worker_lost'",
                args,
            )
            result = {
                f"simweave_suite_jobs_{state}": counts.get(state, 0)
                for state in ("queued", "running", "succeeded", "failed", "cancelled")
            }
            result.update(
                simweave_suite_queue_oldest_seconds=age, simweave_suite_worker_lost_jobs=lost
            )
            if tenant is None:
                result["simweave_workers_fresh"] = value(
                    db,
                    f"SELECT count(*) AS v FROM suite_workers WHERE "
                    f"updated>{NOW}-30 AND state!='offline'",
                )
                result["simweave_suite_lease_losses_total"] = value(
                    db,
                    "SELECT coalesce(sum(value),0) AS v FROM suite_counters WHERE "
                    "name='lease_losses'",
                )
                result["simweave_artifacts_retained"] = value(
                    db, "SELECT count(*) AS v FROM artifacts"
                )
                counters = {
                    r["name"]: r["value"]
                    for r in db.execute("SELECT name,value FROM operation_counters")
                }
                for operation in ("artifact_put", "artifact_get"):
                    for outcome in ("successes_total", "failures_total"):
                        name = operation + "_" + outcome
                        result["simweave_" + name] = counters.get(name, 0)
        return {"schema_version": 1, "metrics": result}


class SharedArtifacts(Artifacts):
    def __init__(self, database, backend):
        if not isinstance(backend, S3):
            raise ValueError("distributed suites require shared S3 storage")
        self.database, self.backend, self.scratch = database, backend, database.scratch

    def inventory_page(self, tenant, after, limit):
        from simweave.integrity import validate_page

        validate_page(tenant, after, limit)
        with self.database.connection() as db:
            rows = db.execute(
                "SELECT digest,size FROM artifacts WHERE tenant=%s AND digest>%s "
                "ORDER BY digest LIMIT %s",
                (tenant, after, limit + 1),
            ).fetchall()
            return [(row["digest"], row["size"]) for row in rows]

    def check_capacity(self, tenant, digest):
        with self.database.connection() as db:
            if (
                value(db, "SELECT count(*) AS v FROM artifacts WHERE tenant=%s", (tenant,)) >= 10000
                and not db.execute(
                    "SELECT 1 FROM artifacts WHERE tenant=%s AND digest=%s", (tenant, digest)
                ).fetchone()
            ):
                raise Capacity("artifact retention capacity reached")

    def retain(self, tenant, digest, size):
        with self.database.connection() as db:
            db.execute("SELECT pg_advisory_xact_lock(191914)")
            exists = db.execute(
                "SELECT size FROM artifacts WHERE tenant=%s AND digest=%s", (tenant, digest)
            ).fetchone()
            if (
                not exists
                and value(db, "SELECT count(*) AS v FROM artifacts WHERE tenant=%s", (tenant,))
                >= 10000
            ):
                raise Capacity("artifact retention capacity reached")
            db.execute(
                "INSERT INTO artifacts VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (tenant, digest, size),
            )

    def size(self, tenant, digest):
        with self.database.connection() as db:
            row = db.execute(
                "SELECT size FROM artifacts WHERE tenant=%s AND digest=%s", (tenant, digest)
            ).fetchone()
            return row["size"] if row else None

    def count_operation(self, name):
        try:
            with self.database.connection() as db:
                db.execute(
                    "INSERT INTO operation_counters VALUES(%s,1) ON "
                    "CONFLICT(name) DO UPDATE SET "
                    "value=operation_counters.value+1",
                    (name,),
                )
        except RuntimeError:
            pass

    def backup(self, target):
        raise ValueError("use PostgreSQL-native backup for distributed metadata")

    def recover(self, tenant, destination):
        raise ValueError("use coordinated PostgreSQL and object-store recovery")
