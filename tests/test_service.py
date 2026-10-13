from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from simweave.api import create_app
from simweave.cli import main
from simweave.config import Settings
from simweave.contracts import Scenario
from simweave.store import LostClaim, Store
from simweave.worker import work_once

TOKEN_A = "a" * 40
TOKEN_B = "b" * 40
AUTH_A = {"Authorization": f"Bearer {TOKEN_A}"}
AUTH_B = {"Authorization": f"Bearer {TOKEN_B}"}


@pytest.fixture
def service(tmp_path):
    app = create_app(Settings(tmp_path / "runs.sqlite3", {TOKEN_A: "alpha", TOKEN_B: "beta"}))
    with TestClient(app) as client:
        yield client, app.state.store


def submit(client, scenario=None, headers=None):
    return client.post("/api/v1/runs", json=scenario or {}, headers=headers or AUTH_A)


def test_gazebo_availability_is_enforced_before_queueing(service, monkeypatch):
    client, store = service
    monkeypatch.setattr("simweave.api.gazebo_available", lambda: False)
    capabilities = client.get("/api/v1/capabilities", headers=AUTH_A).json()
    assert next(a for a in capabilities["adapters"] if a["id"] == "gazebo")["available"] is False
    assert submit(client, {"adapter": "gazebo"}).status_code == 422
    assert store.list("alpha", 30, None) == []


def test_service_full_run_export_and_offline_replay(service, tmp_path):
    client, store = service
    created = submit(client)
    assert created.status_code == 202, created.text
    identifier = created.json()["id"]
    assert work_once(store)
    run = client.get(f"/api/v1/runs/{identifier}", headers=AUTH_A).json()
    assert run["status"] == "succeeded"
    assert run["result"]["passed"]
    samples = client.get(f"/api/v1/runs/{identifier}/telemetry?limit=100", headers=AUTH_A).json()
    assert samples["next_after"] == 99
    assert len(samples["items"]) == 100
    assert client.post(f"/api/v1/runs/{identifier}/verify", headers=AUTH_A).json()["verified"]
    download = client.get(f"/api/v1/runs/{identifier}/recording", headers=AUTH_A)
    path = tmp_path / "recording.jsonl"
    path.write_text(download.text, encoding="utf-8")
    assert main(["replay", str(path)]) == 0
    assert len(download.text.splitlines()) == 602
    # Durable across repository instances (no in-memory queue).
    assert Store(store.path).get("alpha", identifier)["result"] == run["result"]


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("get", ""),
        ("get", "/telemetry"),
        ("get", "/recording"),
        ("post", "/verify"),
        ("post", "/cancel"),
        ("delete", ""),
    ],
)
def test_cross_tenant_objects_are_hidden(service, method, suffix):
    client, store = service
    identifier = submit(client).json()["id"]
    assert (
        getattr(client, method)(f"/api/v1/runs/{identifier}{suffix}", headers=AUTH_B).status_code
        == 404
    )
    assert client.get("/api/v1/runs", headers=AUTH_B).json()["items"] == []


def test_authentication_required_and_input_errors_redacted(service):
    client, _ = service
    assert client.get("/api/v1/runs").status_code == 401
    assert client.post("/api/v1/runs", json={}).status_code == 401
    response = submit(client, {"seed": "private-synthetic-input"})
    assert response.status_code == 422
    assert "private-synthetic-input" not in response.text
    assert client.post("/api/v1/runs", content="x" * 65537, headers=AUTH_A).status_code == 413


def test_idempotency_conflict_and_tenant_scope(service):
    client, _ = service
    auth = AUTH_A | {"Idempotency-Key": "request-1"}
    first = submit(client, headers=auth)
    again = submit(client, headers=auth)
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    assert submit(client, {"seed": 5}, headers=auth).status_code == 409
    assert submit(client, headers=AUTH_B | {"Idempotency-Key": "request-1"}).status_code == 202


def test_queue_quota_cancellation_and_delete(service):
    client, store = service
    identifiers = [submit(client).json()["id"] for _ in range(20)]
    assert submit(client).status_code == 429
    assert client.delete(f"/api/v1/runs/{identifiers[0]}", headers=AUTH_A).status_code == 409
    assert (
        client.post(f"/api/v1/runs/{identifiers[0]}/cancel", headers=AUTH_A).json()["status"]
        == "cancelled"
    )
    assert submit(client).status_code == 202
    assert client.delete(f"/api/v1/runs/{identifiers[0]}", headers=AUTH_A).status_code == 204
    assert store.get("alpha", identifiers[0]) is None


def test_concurrent_claims_and_idempotency_are_atomic(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.submit("alpha", Scenario(), "same"), range(8)))
    assert sum(created for _, created in results) == 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        claimed = list(pool.map(lambda i: store.claim(str(i)), range(8)))
    assert sum(job is not None for job in claimed) == 1


def test_cancelled_or_expired_claim_cannot_publish(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    identifier = store.submit("alpha", Scenario())[0]["id"]
    store.claim("worker")
    store.cancel("alpha", identifier)
    with pytest.raises(LostClaim):
        store.append(identifier, "worker", [])
    assert not store.finish(identifier, "worker", None, "ignored")
    other = store.submit("alpha", Scenario())[0]["id"]
    store.claim("worker")
    with store.connect() as db:
        db.execute("UPDATE runs SET lease_until=0 WHERE id=?", (other,))
    assert store.claim("new-worker") is None
    assert store.get("alpha", other)["error"] == "worker_lost"
    assert not store.finish(other, "worker", None, "ignored")


def test_telemetry_corruption_detected(service):
    client, store = service
    identifier = submit(client).json()["id"]
    work_once(store)
    with store.connect() as db:
        db.execute("DELETE FROM samples WHERE run_id=? AND step=3", (identifier,))
    assert client.post(f"/api/v1/runs/{identifier}/verify", headers=AUTH_A).status_code == 409


def test_cursor_pagination_has_no_overlap(service):
    client, _ = service
    for _ in range(3):
        submit(client)
    page = client.get("/api/v1/runs?limit=2", headers=AUTH_A).json()
    after = client.get(f"/api/v1/runs?limit=2&before={page['next_before']}", headers=AUTH_A).json()
    assert len(page["items"]) == 2
    assert len(after["items"]) == 1
    assert page["items"][0]["id"] != after["items"][0]["id"]


@pytest.mark.parametrize("tokens", [{}, {"short": "tenant"}, {TOKEN_A: "bad tenant"}, []])
def test_invalid_service_config_rejected(tmp_path, tokens):
    with pytest.raises(ValueError):
        Settings(tmp_path / "db", tokens)


def test_failed_gates_are_completed_experiments(service):
    client, store = service
    identifier = submit(client, {"world": {"steps": 1}}).json()["id"]
    work_once(store)
    run = store.get("alpha", identifier)
    assert run["status"] == "succeeded"
    assert not run["result"]["passed"]


def test_worker_failure_is_sanitized(service, monkeypatch):
    client, store = service
    identifier = submit(client).json()["id"]

    def fail(*args):
        raise RuntimeError("private synthetic engine diagnostic")

    monkeypatch.setattr("simweave.worker.execute", fail)
    work_once(store)
    run = store.get("alpha", identifier)
    assert run["status"] == "failed"
    assert run["error"] == "execution_failed"


def test_openapi_and_version_are_unambiguous(service):
    client, _ = service
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"Scenario", "RunView", "RunsPage", "TelemetryPage"} <= schemas.keys()
    assert submit(client, {"schema_version": True}).status_code == 422
    assert client.get("/api/v1/capabilities", headers=AUTH_A).status_code == 200
