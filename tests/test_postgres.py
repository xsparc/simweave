"""Run explicitly against a disposable database named simweave_test."""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from simweave import maintenance
from simweave.postgres import Database, Jobs
from simweave.store import Capacity, Conflict, LostClaim
from simweave.suites import Suite

DSN = os.environ.get("SIMWEAVE_TEST_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(
    not DSN, reason="disposable PostgreSQL integration DSN not configured"
)


@pytest.fixture
def jobs(tmp_path, monkeypatch):
    assert DSN and DSN.endswith("/simweave_test"), "use a dedicated simweave_test database"
    monkeypatch.setenv("SIMWEAVE_POSTGRES_DSN", DSN)
    database = Database(tmp_path, initialize=True)
    with database.connection() as db:
        db.execute(
            "TRUNCATE suite_jobs_v1,suite_workers,suite_counters,artifacts,operation_counters"
        )
        db.execute("UPDATE admission SET paused=false")
    yield Jobs(database)
    database.close()


def suite():
    return Suite.model_validate(
        {
            "name": "postgres",
            "scenarios": [{"world": {"steps": 5}}],
            "seeds": [1],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {},
        }
    )


def test_artifact_inventory_page_is_scoped_and_bounded(jobs):
    from simweave.artifacts import S3
    from simweave.postgres import SharedArtifacts

    # This test queries real PostgreSQL; it never performs object-store I/O.
    storage = SharedArtifacts(jobs.database, object.__new__(S3))
    for tenant in ("alpha", "beta"):
        for index in range(4):
            storage.retain(tenant, f"{index:064x}", index + 1)
    assert storage.inventory_page("alpha", "", 2) == [(f"{i:064x}", i + 1) for i in range(3)]
    assert storage.inventory_page("alpha", f"{1:064x}", 2) == [(f"{i:064x}", i + 1) for i in (2, 3)]
    assert storage.inventory_page("unknown", "", 2) == []
    with pytest.raises(ValueError):
        storage.inventory_page("alpha", "", 26)


def test_concurrent_idempotency_and_tenant_isolation(jobs):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: jobs.submit("alpha", suite(), "same"), range(24)))
    assert len({r["id"] for r in results}) == 1
    assert jobs.get("beta", results[0]["id"]) is None
    assert jobs.cancel("beta", results[0]["id"]) is None
    assert jobs.retry("beta", results[0]["id"]) is None
    assert jobs.list("beta") == []
    other = suite().model_copy(update={"name": "changed"})
    with pytest.raises(Conflict):
        jobs.submit("alpha", other, "same")


def test_parallel_claims_and_stale_attempt_fences(jobs):
    for i in range(24):
        jobs.submit("alpha", suite(), str(i))
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(pool.map(lambda i: jobs.claim("worker-" + str(i)), range(24)))
    assert len({c["id"] for c in claims}) == 24
    assert jobs.claim() is None
    lost = claims[0]
    with jobs.database.connection() as db:
        db.execute("UPDATE suite_jobs_v1 SET lease=0 WHERE id=%s", (lost["id"],))
    assert jobs.expire() == 1
    assert not jobs.finish(lost["id"], lost["claim"], "0" * 64, 0)
    with pytest.raises(LostClaim):
        jobs.heartbeat(lost["id"], lost["claim"])
    assert jobs.retry("alpha", lost["id"])["attempt"] == 1
    new = jobs.claim()
    assert new["id"] == lost["id"] and new["claim"] != lost["claim"]
    assert not jobs.finish(lost["id"], lost["claim"], "0" * 64, 0)
    assert jobs.finish(new["id"], new["claim"], "1" * 64, 0)
    jobs.cancel("alpha", claims[1]["id"])
    assert not jobs.finish(claims[1]["id"], claims[1]["claim"], "2" * 64, 0)


def test_server_clock_and_metrics(jobs, monkeypatch):
    import time

    monkeypatch.setattr(time, "time", lambda: 1)
    job = jobs.submit("alpha", suite(), "one")
    assert job["created"] > 1_000_000_000
    claim = jobs.claim("worker")
    jobs.heartbeat(claim["id"], claim["claim"])
    metrics = jobs.metrics(None, "alpha")["metrics"]
    assert metrics["simweave_suite_jobs_running"] == 1
    assert "simweave_workers_fresh" not in metrics
    assert jobs.metrics(None)["metrics"]["simweave_workers_fresh"] == 1


def test_pause_drain_and_explicit_stopped_acknowledgement(jobs):
    job = jobs.submit("alpha", suite(), "one")
    claim = jobs.claim("worker")
    jobs.cancel("alpha", job["id"])
    with pytest.raises(Conflict):
        maintenance.drain(jobs, 0)
    assert jobs.gate.paused() and jobs.claim() is None
    with pytest.raises(Conflict):
        jobs.submit("alpha", suite(), "two")
    assert maintenance.acknowledge_stopped(jobs, True)["cleared_workers"] == 1
    assert maintenance.drain(jobs, 0)["drained"]
    assert not jobs.finish(claim["id"], claim["claim"])
    jobs.gate.set(False)
    assert jobs.submit("alpha", suite(), "two")["status"] == "queued"


def test_global_and_tenant_quota_are_transactional(jobs):
    payload = suite().model_dump_json()
    with jobs.database.connection() as db:
        db.execute(
            "INSERT INTO "
            "suite_jobs_v1(id,tenant,request_key,suite,digest,status,created,updated) "
            "SELECT 'fixture-'||i,'alpha','key-'||i,%s,%s,'queued',1,1 "
            "FROM generate_series(1,999) i",
            (payload, suite().digest()),
        )

    def submit(i):
        try:
            return jobs.submit("beta", suite(), "parallel-" + str(i))
        except Capacity:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(r is not None for r in pool.map(submit, range(8))) == 1
    with jobs.database.connection() as db:
        db.execute("UPDATE suite_jobs_v1 SET status='succeeded'")
    jobs.submit("alpha", suite(), "last")
    with pytest.raises(Capacity):
        jobs.submit("alpha", suite(), "over")


def test_locked_job_is_skipped(jobs):
    first = jobs.submit("alpha", suite(), "one")
    second = jobs.submit("alpha", suite(), "two")
    with jobs.database.connection() as db:
        db.execute("SELECT id FROM suite_jobs_v1 WHERE id=%s FOR UPDATE", (first["id"],))
        with ThreadPoolExecutor() as pool:
            claim = pool.submit(jobs.claim).result(timeout=5)
        assert claim["id"] == second["id"]


def test_postgres_checkpoint_fails_before_pause(jobs, tmp_path):
    with pytest.raises(ValueError):
        maintenance.checkpoint(jobs, None, tmp_path / "catalogs", tmp_path / "backup")
    assert not jobs.gate.paused() and not (tmp_path / "backup").exists()


def test_api_shared_factory_lifecycle_and_sanitized_failure(jobs, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from simweave import storage_config
    from simweave.api import create_app
    from simweave.artifacts import S3
    from simweave.config import Settings
    from simweave.postgres import Unavailable

    # No network object call is needed to exercise API pool lifetime and queue errors.
    monkeypatch.setattr(storage_config, "backend", lambda path: object.__new__(S3))
    app = create_app(
        Settings(
            tmp_path / "api.sqlite3",
            {"a" * 32: "alpha"},
            artifact_backend=tmp_path / "storage.json",
            postgres=True,
        )
    )
    headers = {"Authorization": "Bearer " + "a" * 32}
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/suite-jobs",
            json=suite().model_dump(),
            headers={**headers, "Idempotency-Key": "api"},
        )
        assert response.status_code == 202

        def unavailable(*args):
            raise Unavailable("private fixture diagnostics")

        monkeypatch.setattr(app.state.suite_jobs, "list", unavailable)
        response = client.get("/api/v1/suite-jobs", headers=headers)
        assert response.status_code == 503
        assert response.json() == {"detail": "suite storage unavailable"}
    assert app.state.suite_jobs.database.pool.closed
    assert app.state.suite_jobs.database.gates.closed
