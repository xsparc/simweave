import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from simweave.api import create_app
from simweave.artifacts import key
from simweave.config import Settings
from simweave.observability import prometheus, snapshot
from simweave.recovery import checkpoint, restore, verify
from simweave.suite_jobs import work_once
from simweave.suites import Suite, execute_suite


def suite(seed=1):
    return Suite.model_validate(
        {
            "name": "connected",
            "scenarios": [
                {"world": {"steps": 5}, "gates": [{"metric": "rmse", "threshold": 10.0}]}
            ],
            "seeds": [seed],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {},
        }
    )


def settings(root):
    return Settings(
        root / "runs.sqlite3",
        {
            "a" * 32: "alpha",
            "b" * 32: "beta",
            "i" * 32: {"tenant": "alpha", "subject": "importer", "role": "importer"},
            "r" * 32: {"tenant": "alpha", "subject": "reader", "role": "reader"},
            "z" * 32: {"tenant": "beta", "subject": "importer", "role": "importer"},
        },
    )


def auth(token):
    return {"Authorization": "Bearer " + token * 32}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return create_app(settings(tmp_path))


def test_job_review_download_and_isolation(app, tmp_path):
    jobs, artifacts = app.state.suite_jobs, app.state.artifacts
    item = jobs.submit("alpha", suite(), "one")
    assert work_once(jobs, artifacts)
    with TestClient(app) as client:
        path = f"/api/v1/suite-jobs/{item['id']}/artifact"
        response = client.get(path, headers=auth("a"))
        assert response.status_code == 200 and response.content[:2] == b"PK"
        assert client.get(path, headers=auth("b")).status_code == 404
        assert client.get(path, headers=auth("r")).status_code == 403
        route = "/api/v1/catalog/builds/candidate/from-job"
        assert client.post(route, json={"job": item["id"]}, headers=auth("z")).status_code == 404
        assert client.post(route, json={"job": item["id"]}, headers=auth("r")).status_code == 403
        assert client.post(route, json={"job": item["id"]}, headers=auth("i")).status_code == 201
        route = "/api/v1/catalog/builds/candidate/artifact"
        assert client.get(route, headers=auth("r")).content == response.content
        assert client.get(route, headers=auth("z")).status_code == 404
        assert client.get(route, headers=auth("a")).status_code == 403
        for _ in range(4):  # Response cleanup releases both slots and temporary files.
            assert client.get(route, headers=auth("r")).status_code == 200


def test_upload_retains_bytes_before_catalog_and_missing_bytes_fail_closed(app, tmp_path):
    execute_suite(suite(), tmp_path / "suite")
    data = (tmp_path / "suite/evidence.zip").read_bytes()
    with TestClient(app) as client:
        response = client.put(
            "/api/v1/catalog/builds/upload",
            content=data,
            headers={**auth("i"), "Content-Type": "application/zip"},
        )
        assert response.status_code == 201
        build = client.get("/api/v1/catalog/builds/upload", headers=auth("r")).json()
        source = app.state.artifacts.backend.root / key("alpha", build["bundle_digest"])
        assert source.read_bytes() == data
        source.write_bytes(b"bad")
        route = "/api/v1/catalog/builds/upload/artifact"
        assert client.get(route, headers=auth("r")).status_code == 503
        source.write_bytes(data)
        assert client.get(route, headers=auth("r")).status_code == 200
    assert (
        snapshot(app.state.suite_jobs, app.state.artifacts)["metrics"][
            "simweave_artifact_get_failures_total"
        ]
        == 1
    )


def test_failed_retention_never_creates_catalog_build(app, tmp_path, monkeypatch):
    execute_suite(suite(), tmp_path / "suite")

    def failed(*args):
        raise RuntimeError("private backend diagnostic")

    monkeypatch.setattr(app.state.artifacts.backend, "put", failed)
    with TestClient(app) as client:
        response = client.put(
            "/api/v1/catalog/builds/missing",
            content=(tmp_path / "suite/evidence.zip").read_bytes(),
            headers={**auth("i"), "Content-Type": "application/zip"},
        )
        assert response.status_code == 409 and "private" not in response.text
        assert client.get("/api/v1/catalog/builds/missing", headers=auth("r")).status_code == 404


def test_metrics_are_scoped_and_worker_freshness_is_bounded(app):
    jobs, artifacts = app.state.suite_jobs, app.state.artifacts
    jobs.submit("alpha", suite(), "one")
    jobs.worker_ping("synthetic-worker", "idle")
    metrics = snapshot(jobs, artifacts)["metrics"]
    assert metrics["simweave_workers_fresh"] == 1
    assert metrics["simweave_suite_queue_oldest_seconds"] >= 0
    with jobs.db.connect() as db:
        db.execute("UPDATE suite_workers SET updated=0")
    assert snapshot(jobs, artifacts)["metrics"]["simweave_workers_fresh"] == 0
    with TestClient(app) as client:
        response = client.get("/api/v1/suite-metrics", headers=auth("b"))
        assert response.json()["metrics"]["simweave_suite_jobs_queued"] == 0
        assert "workers" not in response.text and "artifact" not in response.text
        assert client.get("/api/v1/suite-metrics").status_code == 401
    text = prometheus(snapshot(jobs, artifacts))
    assert "synthetic-worker" not in text and "alpha" not in text
    assert "# TYPE simweave_artifact_put_failures_total counter" in text


def test_checkpoint_restore_references_and_fresh_target(app, tmp_path):
    jobs, artifacts = app.state.suite_jobs, app.state.artifacts
    item = jobs.submit("alpha", suite(), "one")
    work_once(jobs, artifacts)
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/v1/catalog/builds/candidate/from-job",
                json={"job": item["id"]},
                headers=auth("i"),
            ).status_code
            == 201
        )
    result = checkpoint(
        jobs, artifacts, tmp_path / "runs.sqlite3.catalogs", tmp_path / "checkpoint"
    )
    assert (result["jobs"], result["artifacts"], result["references"]) == (1, 1, 1)
    restore(tmp_path / "checkpoint", tmp_path / "restored")
    restored = create_app(settings(tmp_path / "restored"))
    assert restored.state.suite_jobs.get("alpha", item["id"])["artifact"]
    with TestClient(restored) as client:
        assert (
            client.get("/api/v1/catalog/builds/candidate/artifact", headers=auth("r")).status_code
            == 200
        )
    with pytest.raises(FileExistsError):
        restore(tmp_path / "checkpoint", tmp_path / "restored")
    manifest = tmp_path / "checkpoint/manifest.json"
    value = json.loads(manifest.read_bytes())
    value["files"]["../outside"] = {"size": 1, "sha256": "0" * 64}
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        restore(tmp_path / "checkpoint", tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_checkpoint_rejects_active_work_and_missing_references(app, tmp_path):
    jobs, artifacts = app.state.suite_jobs, app.state.artifacts
    item = jobs.submit("alpha", suite(), "one")
    claim = jobs.claim()
    with pytest.raises(ValueError):
        checkpoint(jobs, artifacts, tmp_path / "runs.sqlite3.catalogs", tmp_path / "active")
    jobs.finish(item["id"], claim["claim"], "0" * 64, 0)
    with pytest.raises(ValueError):
        checkpoint(jobs, artifacts, tmp_path / "runs.sqlite3.catalogs", tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


def test_incomplete_checkpoint_rejected(tmp_path):
    with pytest.raises(OSError):
        verify(tmp_path)


def test_lease_loss_counter_survives_retry(app):
    jobs, artifacts = app.state.suite_jobs, app.state.artifacts
    item = jobs.submit("alpha", suite(), "lost")
    jobs.claim()
    with jobs.db.connect() as db:
        db.execute("UPDATE suite_jobs_v1 SET lease=0")
    assert jobs.expire() == 1
    assert jobs.expire() == 0
    jobs.retry("alpha", item["id"])
    metrics = snapshot(jobs, artifacts)["metrics"]
    assert metrics["simweave_suite_lease_losses_total"] == 1
    assert metrics["simweave_suite_worker_lost_jobs"] == 0


def test_download_send_failure_releases_slot(app, tmp_path):
    import asyncio

    from fastapi import HTTPException

    jobs, artifacts = app.state.suite_jobs, app.state.artifacts
    item = jobs.submit("alpha", suite(), "download")
    work_once(jobs, artifacts)
    digest = jobs.get("alpha", item["id"])["artifact"]
    first = app.state.downloads.response("alpha", digest)
    second = app.state.downloads.response("alpha", digest)
    with pytest.raises(HTTPException) as rejected:
        app.state.downloads.response("alpha", digest)
    assert rejected.value.status_code == 429

    async def send(message):
        raise OSError("synthetic disconnected client")

    async def receive():
        return {"type": "http.disconnect"}

    async def execute():
        with pytest.raises(OSError):
            await first({"type": "http", "method": "GET", "headers": []}, receive, send)

    asyncio.run(execute())
    assert not Path(first.path).exists()
    third = app.state.downloads.response("alpha", digest)
    second.cleanup()
    third.cleanup()


def test_restore_rejects_corrupt_object_and_resets_worker_presence(app, tmp_path):
    jobs, artifacts = app.state.suite_jobs, app.state.artifacts
    jobs.submit("alpha", suite(), "one")
    work_once(jobs, artifacts)
    jobs.worker_ping("idle-before-shutdown", "idle")
    checkpoint(jobs, artifacts, tmp_path / "runs.sqlite3.catalogs", tmp_path / "checkpoint")
    restore(tmp_path / "checkpoint", tmp_path / "restored")
    restored = create_app(settings(tmp_path / "restored"))
    assert (
        snapshot(restored.state.suite_jobs, restored.state.artifacts)["metrics"][
            "simweave_workers_fresh"
        ]
        == 0
    )
    bundle = next((tmp_path / "checkpoint/objects").rglob("*.zip"))
    bundle.write_bytes(b"corruption")
    with pytest.raises(ValueError):
        restore(tmp_path / "checkpoint", tmp_path / "corrupt")
    assert not (tmp_path / "corrupt").exists()
