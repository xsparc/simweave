"""Persistent single-host admission fence; failures never automatically resume work."""

import sqlite3
import time
from contextlib import closing, contextmanager
from functools import wraps

from simweave.store import Conflict


class Gate:
    def __init__(self, queue):
        self.path = queue.with_name(queue.name + ".maintenance")
        with self.connection() as db, db:
            # Rollback journaling is intentional: readers fence the pause/resume commit.
            db.execute(
                "CREATE TABLE IF NOT EXISTS admission (id INTEGER PRIMARY KEY, paused INTEGER)"
            )
            db.execute("INSERT OR IGNORE INTO admission VALUES(1,0)")

    def connection(self):
        return closing(sqlite3.connect(self.path, timeout=5, check_same_thread=False))

    @contextmanager
    def hold(self, paused=False):
        with self.connection() as db:
            db.execute("BEGIN")
            actual = bool(db.execute("SELECT paused FROM admission WHERE id=1").fetchone()[0])
            if actual != paused:
                raise Conflict("maintenance admission is paused" if actual else "pause required")
            yield

    def paused(self):
        with self.connection() as db:
            return bool(db.execute("SELECT paused FROM admission WHERE id=1").fetchone()[0])

    def set(self, paused):
        with self.connection() as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE admission SET paused=? WHERE id=1", (int(paused),))
        return {"schema_version": 1, "paused": paused}


def admitted(operation):
    @wraps(operation)
    def run(self, *args, **kwargs):
        with self.gate.hold():
            return operation(self, *args, **kwargs)

    return run


def drain(jobs, timeout=300):
    if not 0 <= timeout <= 3600:
        raise ValueError("drain timeout must be between zero and 3600 seconds")
    jobs.gate.set(True)
    deadline = time.monotonic() + timeout
    with jobs.gate.hold(paused=True):
        while True:
            if hasattr(jobs, "activity"):
                running, busy = jobs.activity()
            else:
                with jobs.db.connect() as db:
                    running = db.execute(
                        "SELECT count(*) FROM suite_jobs_v1 WHERE status='running'"
                    ).fetchone()[0]
                    busy = db.execute(
                        "SELECT count(*) FROM suite_workers WHERE state='busy'"
                    ).fetchone()[0]
            if not running and not busy:
                return {"schema_version": 1, "paused": True, "drained": True}
            if time.monotonic() >= deadline:
                raise Conflict("drain timed out; admission remains paused; inspect workers")
            time.sleep(0.1)


def checkpoint(jobs, artifacts, catalogs, target, timeout=300, *, object_cache=None):
    from simweave.recovery import checkpoint as snapshot

    if hasattr(jobs, "database"):
        raise ValueError("use PostgreSQL-native and object-store backup after drain")
    drain(jobs, timeout)
    with jobs.gate.hold(paused=True):
        options = {} if object_cache is None else {"object_cache": object_cache}
        result = snapshot(jobs, artifacts, catalogs, target, **options)
    return {**result, "paused": True}


def acknowledge_stopped(jobs, workers_stopped=False):
    """Operator assertion after terminating every source worker, never a lease heuristic."""
    if not workers_stopped:
        raise ValueError("stop all workers and supply --workers-stopped")
    with jobs.gate.hold(paused=True):
        if hasattr(jobs, "acknowledge_stopped"):
            return {
                "schema_version": 1,
                "paused": True,
                "cleared_workers": jobs.acknowledge_stopped(),
            }
        jobs.expire()
        with jobs.db.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM suite_jobs_v1 WHERE status='running'").fetchone()[
                0
            ]:
                raise Conflict("wait for stopped workers' outstanding leases to expire")
            cleared = db.execute("DELETE FROM suite_workers").rowcount
    return {"schema_version": 1, "paused": True, "cleared_workers": cleared}
