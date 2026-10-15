import tempfile

import pytest
from fastapi.testclient import TestClient

from simweave.api import create_app
from simweave.artifacts import Artifacts, Filesystem, key
from simweave.config import Settings
from simweave.store import Conflict, LostClaim
from simweave.suite_jobs import SuiteJobs, work_once
from simweave.suites import Suite, SuiteInterrupted, execute_suite


def suite(seed=1):
    return Suite.model_validate(
        {
            "name": "durable",
            "scenarios": [{"world": {"steps": 20}}],
            "seeds": [seed],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {},
        }
    )


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return Artifacts(tmp_path / "index.db", Filesystem(tmp_path / "objects"))


def test_verified_retention_recovery_and_backup(tmp_path, storage):
    execute_suite(suite(), tmp_path / "suite")
    bundle = tmp_path / "suite/evidence.zip"
    digest = storage.put("alpha", bundle)
    assert storage.put("alpha", bundle) == digest
    with pytest.raises(KeyError):
        storage.get("beta", digest, tmp_path / "forbidden.zip")
    recovered = Filesystem(tmp_path / "recovered")
    assert storage.recover("alpha", recovered) == 1
    storage.backup(tmp_path / "backup.db")
    restored = Artifacts(tmp_path / "backup.db", recovered)
    restored.get("alpha", digest, tmp_path / "restored.zip")
    assert (tmp_path / "restored.zip").read_bytes() == bundle.read_bytes()
    with pytest.raises(FileExistsError):
        restored.get("alpha", digest, tmp_path / "restored.zip")
    # Existing evidence is immutable, including a corrupted backing object.
    (recovered.root / key("alpha", digest)).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        restored.get("alpha", digest, tmp_path / "bad.zip")
    assert not (tmp_path / "bad.zip").exists()
    with pytest.raises(ValueError):
        restored.put("alpha", bundle)
    bundle.write_bytes(b"invalid zip")
    with pytest.raises(ValueError):
        storage.put("alpha", bundle)


@pytest.mark.parametrize("tenant", ["../other", "CON/../x", "UPPER", "", "a" * 65])
def test_tenant_paths_are_closed(tenant):
    with pytest.raises(ValueError):
        key(tenant, "0" * 64)


def test_claim_fencing_cancel_and_explicit_recovery(tmp_path):
    jobs = SuiteJobs(tmp_path / "jobs.db")
    item = jobs.submit("alpha", suite(), "one")
    assert jobs.submit("alpha", suite(), "one") == item
    with pytest.raises(Conflict):
        jobs.submit("alpha", suite(2), "one")
    claim = jobs.claim()
    assert jobs.get("beta", item["id"]) is None
    assert jobs.cancel("beta", item["id"]) is None
    assert jobs.retry("beta", item["id"]) is None
    with jobs.db.connect() as db:
        db.execute("UPDATE suite_jobs_v1 SET lease=0")
    assert not jobs.finish(item["id"], claim["claim"], "0" * 64, 0)
    with pytest.raises(LostClaim):
        jobs.heartbeat(item["id"], claim["claim"])
    assert jobs.expire() == 1
    assert jobs.claim() is None  # Never silently retry.
    assert jobs.get("alpha", item["id"])["error"] == "worker_lost"
    jobs.retry("alpha", item["id"])
    new = jobs.claim()
    assert new["claim"] != claim["claim"]
    assert not jobs.finish(item["id"], claim["claim"], "0" * 64, 0)
    jobs.cancel("alpha", item["id"])
    assert not jobs.finish(item["id"], new["claim"], "0" * 64, 0)
    with pytest.raises(Conflict):
        jobs.retry("alpha", item["id"])


def test_worker_publishes_verified_bundle_and_reports_storage_failure(tmp_path, storage):
    jobs = SuiteJobs(tmp_path / "jobs.db")
    item = jobs.submit("alpha", suite(), "one")
    assert work_once(jobs, storage)
    result = jobs.get("alpha", item["id"])
    assert result["status"] == "succeeded"
    assert result["exit_code"] in (0, 1)
    storage.get("alpha", result["artifact"], tmp_path / "published.zip")
    assert not work_once(jobs, storage)
    item = jobs.submit("alpha", suite(), "two")

    class Unavailable:
        def put(self, *args):
            raise OSError("synthetic private detail")

    assert work_once(jobs, Unavailable())
    assert jobs.get("alpha", item["id"])["error"] == "execution_or_storage_failed"


def test_checkpoint_interrupt_is_not_a_case_error(tmp_path):
    calls = 0

    def checkpoint():
        nonlocal calls
        calls += 1
        if calls == 3:
            raise SuiteInterrupted()

    with pytest.raises(SuiteInterrupted):
        execute_suite(suite(), tmp_path / "suite", checkpoint=checkpoint)
    assert not (tmp_path / "suite/evidence.zip").exists()


def test_cancel_during_publication_fences_success(tmp_path, storage):
    jobs = SuiteJobs(tmp_path / "jobs.db")
    item = jobs.submit("alpha", suite(), "cancel-running")

    class CancelDuringPut:
        def put(self, tenant, source):
            jobs.cancel(tenant, item["id"])
            return storage.put(tenant, source)

    assert work_once(jobs, CancelDuringPut())
    result = jobs.get("alpha", item["id"])
    assert result["status"] == "cancelled"
    assert result["artifact"] is None
    # The interrupted publication is retained conservatively, never auto-deleted.
    assert storage.recover("alpha", Filesystem(tmp_path / "recovery")) == 1


def test_failed_upload_does_not_publish_metadata(tmp_path, storage):
    execute_suite(suite(), tmp_path / "suite")

    class FailingBackend:
        def put(self, *args):
            raise RuntimeError("unavailable")

    storage.backend = FailingBackend()
    with pytest.raises(RuntimeError):
        storage.put("alpha", tmp_path / "suite/evidence.zip")
    with storage.db.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0


def test_retries_are_bounded(tmp_path):
    jobs = SuiteJobs(tmp_path / "jobs.db")
    item = jobs.submit("alpha", suite(), "retry")
    for attempt in range(5):
        claim = jobs.claim()
        jobs.finish(item["id"], claim["claim"], error="execution_or_storage_failed")
        if attempt < 4:
            jobs.retry("alpha", item["id"])
    with pytest.raises(Conflict):
        jobs.retry("alpha", item["id"])


def test_s3_boundary_without_optional_dependency_is_lazy():
    # Core import and filesystem use do not import boto3.
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import simweave.artifacts; assert 'boto3' not in sys.modules",
        ],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0


def test_suite_api_authority_isolation_and_conflicts(tmp_path):
    app = create_app(
        Settings(
            tmp_path / "api.db",
            {
                "a" * 32: "alpha",
                "b" * 32: "beta",
                "c" * 32: {"tenant": "alpha", "subject": "reader", "role": "reader"},
            },
        )
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + "a" * 32, "Idempotency-Key": "one"}
        response = client.post("/api/v1/suite-jobs", json=suite().model_dump(), headers=headers)
        assert response.status_code == 202
        identifier = response.json()["id"]
        route = f"/api/v1/suite-jobs/{identifier}"
        assert client.get(route).status_code == 401
        for suffix in ("", "/cancel", "/retry"):
            request = client.post if suffix else client.get
            assert (
                request(route + suffix, headers={"Authorization": "Bearer " + "b" * 32}).status_code
                == 404
            )
        assert client.get(route, headers={"Authorization": "Bearer " + "c" * 32}).status_code == 403
        assert (
            client.post(
                "/api/v1/suite-jobs", json=suite(2).model_dump(), headers=headers
            ).status_code
            == 409
        )
        assert client.post(route + "/retry", headers=headers).status_code == 409
        assert client.post(route + "/cancel", headers=headers).json()["status"] == "cancelled"
        assert len(client.get("/api/v1/suite-jobs", headers=headers).json()["items"]) == 1
