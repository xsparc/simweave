import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from simweave import maintenance, recovery
from simweave.api import create_app
from simweave.artifacts import Artifacts, Filesystem
from simweave.config import Settings
from simweave.store import Conflict
from simweave.suite_jobs import SuiteJobs, work_once
from simweave.suites import Suite


def setup(root):
    jobs = SuiteJobs(root / "queue")
    artifacts = Artifacts(root / "index", Filesystem(root / "objects"))
    suite = Suite.model_validate(
        {
            "name": "drain",
            "scenarios": [
                {"world": {"steps": 5}, "gates": [{"metric": "rmse", "threshold": 10.0}]}
            ],
            "seeds": [1],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {},
        }
    )
    return jobs, artifacts, suite


def test_pause_persists_and_blocks_admission(tmp_path):
    jobs, artifacts, suite = setup(tmp_path)
    item = jobs.submit("alpha", suite, "one")
    jobs.gate.set(True)
    reopened = SuiteJobs(jobs.db.path)
    assert reopened.gate.paused()
    with pytest.raises(Conflict):
        reopened.submit("alpha", suite, "two")
    assert reopened.claim() is None
    assert not work_once(reopened, artifacts)
    assert reopened.get("alpha", item["id"])["status"] == "queued"
    reopened.gate.set(False)
    assert work_once(reopened, artifacts)


def test_four_workers_drain_without_claiming_next_jobs(tmp_path, monkeypatch):
    jobs, artifacts, suite = setup(tmp_path)
    for i in range(8):
        jobs.submit("alpha" if i % 2 else "beta", suite, str(i))
    entered = threading.Barrier(5)
    release = threading.Event()
    original = artifacts.put

    def put(*args):
        entered.wait(timeout=15)
        assert release.wait(15)
        return original(*args)

    monkeypatch.setattr(artifacts, "put", put)
    with ThreadPoolExecutor(max_workers=5) as pool:
        workers = [pool.submit(work_once, jobs, artifacts, f"worker-{i}") for i in range(4)]
        entered.wait(timeout=15)
        jobs.gate.set(True)
        with pytest.raises(Conflict, match="timed out"):
            maintenance.drain(jobs, 0)
        release.set()
        assert all(f.result(timeout=20) for f in workers)
        assert maintenance.drain(jobs, 5)["drained"]
    with jobs.db.connect() as db:
        assert (
            db.execute("SELECT count(*) FROM suite_jobs_v1 WHERE status='succeeded'").fetchone()[0]
            == 4
        )
        assert (
            db.execute("SELECT count(*) FROM suite_jobs_v1 WHERE status='queued'").fetchone()[0]
            == 4
        )
    assert not work_once(jobs, artifacts)
    jobs.gate.set(False)
    monkeypatch.setattr(artifacts, "put", original)
    assert work_once(jobs, artifacts)


@pytest.mark.parametrize("point", ["after-pause", "during-copy", "after-publication"])
def test_interruption_retains_pause_and_all_references(tmp_path, monkeypatch, point):
    jobs, artifacts, suite = setup(tmp_path)
    item = jobs.submit("alpha", suite, "one")
    assert work_once(jobs, artifacts)
    catalogs = tmp_path / "catalogs"
    target = tmp_path / "checkpoint"
    owner, name = {
        "after-pause": (maintenance, "drain"),
        "during-copy": (artifacts.backend, "get"),
        "after-publication": (recovery, "checkpoint"),
    }[point]
    original = getattr(owner, name)

    def interrupted(*args):
        original(*args)
        raise OSError("synthetic interruption")

    monkeypatch.setattr(owner, name, interrupted)
    with pytest.raises(OSError):
        maintenance.checkpoint(jobs, artifacts, catalogs, target)
    assert jobs.gate.paused()
    assert target.exists() == (point == "after-publication")
    monkeypatch.setattr(owner, name, original)
    jobs = SuiteJobs(jobs.db.path)
    if not target.exists():
        maintenance.checkpoint(jobs, artifacts, catalogs, target)
    assert jobs.gate.paused()
    assert recovery.verify(target)["references"] == 1
    restored = tmp_path / "restored"
    result = recovery.restore(target, restored)
    assert result["references"] == 1
    recovered = SuiteJobs(restored / "runs.sqlite3.suites")
    assert recovered.gate.paused()
    assert (
        recovered.get("alpha", item["id"])["artifact"] == jobs.get("alpha", item["id"])["artifact"]
    )
    recovered.gate.set(False)
    assert recovered.submit("alpha", suite, "two")["status"] == "queued"


def test_cancelled_busy_worker_is_not_drained(tmp_path):
    jobs, _, suite = setup(tmp_path)
    item = jobs.submit("alpha", suite, "one")
    jobs.worker_ping("worker", "idle")
    jobs.claim("worker")
    jobs.cancel("alpha", item["id"])
    with pytest.raises(Conflict):
        maintenance.drain(jobs, 0)
    jobs.worker_ping("worker", "offline")
    assert maintenance.drain(jobs, 0)["drained"]


def test_pause_waits_for_admitted_transaction(tmp_path):
    jobs, _, _ = setup(tmp_path)
    started = threading.Event()
    with ThreadPoolExecutor() as pool:
        with jobs.gate.hold():

            def pause():
                started.set()
                return jobs.gate.set(True)

            pending = pool.submit(pause)
            assert started.wait(5)
            assert not pending.done()
        assert pending.result(timeout=6)["paused"]
    with pytest.raises(Conflict):
        with jobs.gate.hold():
            pass


def test_maintenance_blocks_catalog_writes_but_not_reads(tmp_path):
    app = create_app(
        Settings(
            tmp_path / "runs",
            {
                "a" * 32: "alpha",
                "i" * 32: {"tenant": "alpha", "subject": "importer", "role": "importer"},
            },
        )
    )
    app.state.suite_jobs.gate.set(True)
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + "i" * 32}
        assert client.get("/api/v1/catalog", headers=headers).status_code == 200
        assert (
            client.post(
                "/api/v1/catalog/comparisons", headers=headers, json={"build": "missing"}
            ).status_code
            == 409
        )
        assert (
            client.put(
                "/api/v1/catalog/builds/test",
                headers={**headers, "Content-Type": "application/zip"},
                content=b"bad",
            ).status_code
            == 409
        )
        assert client.get("/static/workspace.html").status_code == 200


def test_restore_failure_never_publishes_destination(tmp_path, monkeypatch):
    jobs, artifacts, suite = setup(tmp_path)
    jobs.submit("alpha", suite, "one")
    work_once(jobs, artifacts)
    maintenance.checkpoint(jobs, artifacts, tmp_path / "catalogs", tmp_path / "checkpoint")
    original = recovery.verify
    calls = 0

    def interrupt(root):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic copied-byte verification failure")
        return original(root)

    monkeypatch.setattr(recovery, "verify", interrupt)
    with pytest.raises(OSError):
        recovery.restore(tmp_path / "checkpoint", tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_stale_busy_workers_require_explicit_stopped_acknowledgement(tmp_path):
    jobs, _, suite = setup(tmp_path)
    jobs.submit("alpha", suite, "one")
    jobs.worker_ping("lost", "idle")
    jobs.claim("lost")
    jobs.gate.set(True)
    with pytest.raises(ValueError):
        maintenance.acknowledge_stopped(jobs)
    with pytest.raises(Conflict):
        maintenance.acknowledge_stopped(jobs, True)
    with jobs.db.connect() as db:
        db.execute("UPDATE suite_jobs_v1 SET lease=0")
    assert maintenance.acknowledge_stopped(jobs, True)["cleared_workers"] == 1
    assert maintenance.drain(jobs, 0)["drained"]
    assert jobs.list("alpha")[0]["error"] == "worker_lost"


def test_pause_blocks_retry_and_concurrent_resume(tmp_path):
    jobs, _, suite = setup(tmp_path)
    job = jobs.submit("alpha", suite, "one")
    claim = jobs.claim()
    jobs.finish(job["id"], claim["claim"], error="synthetic")
    jobs.gate.set(True)
    with pytest.raises(Conflict):
        jobs.retry("alpha", job["id"])
    started = threading.Event()
    with ThreadPoolExecutor() as pool:
        with jobs.gate.hold(paused=True):

            def resume():
                started.set()
                return jobs.gate.set(False)

            pending = pool.submit(resume)
            assert started.wait(5)
            assert not pending.done()
        assert not pending.result(timeout=6)["paused"]
    assert jobs.retry("alpha", job["id"])["status"] == "queued"


def test_claim_registers_busy_worker_even_if_idle_presence_was_evicted(tmp_path):
    jobs, _, suite = setup(tmp_path)
    item = jobs.submit("alpha", suite, "one")
    jobs.claim("worker-without-idle-row")
    jobs.cancel("alpha", item["id"])
    with pytest.raises(Conflict):
        maintenance.drain(jobs, 0)


def test_busy_worker_capacity_is_bounded_without_evicting_live_records(tmp_path):
    from simweave.store import Capacity

    jobs, _, suite = setup(tmp_path)
    with jobs.db.connect() as db:
        db.executemany(
            "INSERT INTO suite_workers VALUES(?,0,'busy')", [(str(i),) for i in range(1024)]
        )
    jobs.submit("alpha", suite, "one")
    with pytest.raises(Capacity):
        jobs.worker_ping("new", "idle")
    with pytest.raises(Capacity):
        jobs.claim("new")
    assert jobs.list("alpha")[0]["status"] == "queued"
    jobs.worker_ping("0", "offline")
    assert jobs.claim("new")
    with jobs.db.connect() as db:
        assert db.execute("SELECT count(*) FROM suite_workers").fetchone()[0] == 1024
