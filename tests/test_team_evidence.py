import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from simweave import catalog_archive, history
from simweave.api import create_app
from simweave.cli import main
from simweave.config import Settings
from simweave.contracts import canonical
from simweave.statistics import DecisionPolicy
from simweave.suites import Suite, execute_suite


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    path = tmp_path_factory.mktemp("team") / "runs"
    execute_suite(
        Suite.model_validate(
            {
                "name": "Archive fixture",
                "scenarios": [
                    {
                        "name": "cart",
                        "world": {"steps": 5},
                        "gates": [{"metric": "rmse", "threshold": 10.0}],
                    }
                ],
                "seeds": [1, 2],
                "adapters": ["reference"],
                "baseline": {},
                "candidate": {"kp": 8.1},
            }
        ),
        path,
    )
    return path / "evidence.zip"


@pytest.fixture
def policy():
    return DecisionPolicy.model_validate(
        {"metrics": [{"metric": "rmse", "max_increase": 0.02}], "resamples": 1000}
    )


@pytest.fixture
def catalog(tmp_path, bundle, policy, monkeypatch):
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    path = tmp_path / "catalog.db"
    history.initialize(path)
    history.add_build(path, bundle, "base", "baseline")
    history.add_build(path, bundle, "candidate")
    for generation in range(2):
        history.change_baseline(
            path,
            history.Approval(
                expected_generation=generation, approved_by="reviewer", reason="verified"
            ),
            build="base",
            policy=policy,
        )
    history.change_baseline(
        path,
        history.Approval(expected_generation=2, approved_by="reviewer", reason="rollback"),
        restore=1,
    )
    history.compare_build(path, "candidate")
    return path


def test_archive_cli_roundtrip_and_no_overwrite(catalog, tmp_path):
    archive, restored = tmp_path / "catalog.ndjson", tmp_path / "restored.db"
    assert main(["history", "export", "--database", str(catalog), str(archive)]) == 0
    assert main(["history", "restore", "--database", str(restored), str(archive)]) == 0
    assert history.snapshot(catalog) == history.snapshot(restored)
    second = tmp_path / "second.ndjson"
    catalog_archive.export_catalog(restored, second)
    assert second.read_bytes() == archive.read_bytes()
    with pytest.raises(FileExistsError):
        catalog_archive.restore_catalog(archive, restored)
    with pytest.raises(FileExistsError):
        catalog_archive.export_catalog(catalog, archive)
    with sqlite3.connect(restored) as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute("DELETE FROM events")


def rewrite(records):
    lines = [(canonical(r) + "\n").encode() for r in records[:-1]]
    records[-1]["sha256"] = hashlib.sha256(b"".join(lines)).hexdigest()
    return b"".join(lines) + (canonical(records[-1]) + "\n").encode()


@pytest.mark.parametrize(
    "damage",
    [
        "truncated",
        "trailing",
        "checksum",
        "duplicate",
        "order",
        "generation",
        "build",
        "policy",
        "comparison",
        "unknown",
        "version",
        "timestamp",
    ],
)
def test_archive_rejects_corruption_without_destination(catalog, tmp_path, damage):
    archive = tmp_path / "archive.ndjson"
    catalog_archive.export_catalog(catalog, archive)
    data = archive.read_bytes()
    records = [json.loads(line) for line in data.splitlines()]
    if damage == "truncated":
        data = data[:-5]
    elif damage == "trailing":
        data += b"\n"
    elif damage == "checksum":
        data = data.replace(b"verified", b"tampered", 1)
    else:
        if damage == "duplicate":
            records.insert(2, records[1])
        elif damage == "order":
            records[1], records[3] = records[3], records[1]
        elif damage == "unknown":
            records[1]["table"] = "arbitrary"
        elif damage == "version":
            records[0]["schema_version"] = True
        else:
            record = (
                records[5]
                if damage == "policy"
                else records[6]
                if damage == "comparison"
                else records[3]
            )
            if damage == "generation":
                record["payload"]["approval"]["expected_generation"] = 9
            elif damage == "build":
                record["payload"]["build"] = "missing"
            elif damage == "policy":
                record["payload"]["policy"]["resamples"] = 1001
            elif damage == "timestamp":
                record["payload"]["recorded_at"] = "2026-10-14"
            else:
                record["payload"]["candidate_digest"] = "0" * 64
            record["digest"] = hashlib.sha256(canonical(record["payload"]).encode()).hexdigest()
        data = rewrite(records)
    archive.write_bytes(data)
    destination = tmp_path / "rejected.db"
    with pytest.raises((ValueError, sqlite3.Error)):
        catalog_archive.restore_catalog(archive, destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".catalog-restore-*"))


def test_archive_bounds(catalog, tmp_path, monkeypatch):
    archive = tmp_path / "archive.ndjson"
    catalog_archive.export_catalog(catalog, archive)
    monkeypatch.setattr(catalog_archive, "MAX_ARCHIVE", 100)
    with pytest.raises(ValueError):
        catalog_archive.restore_catalog(archive, tmp_path / "reject.db")
    with pytest.raises(ValueError):
        catalog_archive.export_catalog(catalog, tmp_path / "reject.ndjson")
    assert not (tmp_path / "reject.ndjson").exists()


def credentials(tenant, role):
    return {"Authorization": "Bearer " + (tenant + "_" + role).ljust(32, "_")}


@pytest.fixture
def service(tmp_path, monkeypatch):
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    tokens = {
        (tenant + "_" + role).ljust(32, "_"): {
            "tenant": tenant,
            "subject": tenant + "." + role,
            "role": role,
        }
        for tenant in ("alpha", "beta")
        for role in ("reader", "importer", "approver")
    }
    tokens["legacy".ljust(32, "_")] = "alpha"
    settings = Settings(tmp_path / "runs.db", tokens)
    return TestClient(create_app(settings)), settings


def upload(client, bundle, tenant="alpha", role="importer", label="base"):
    return client.put(
        "/api/v1/catalog/builds/" + label,
        headers={**credentials(tenant, role), "Content-Type": "application/zip"},
        content=bundle.read_bytes(),
    )


def test_roles_isolation_restart_and_approval(service, bundle, policy):
    client, settings = service
    base = "/api/v1/catalog"
    assert client.get(base).status_code == 401
    assert client.get(base, headers=credentials("alpha", "reader")).status_code == 200
    assert (
        client.get(base, headers={"Authorization": "Bearer " + "legacy".ljust(32, "_")}).status_code
        == 403
    )
    for role in ("reader", "approver"):
        assert upload(client, bundle, role=role).status_code == 403
    assert upload(client, bundle).status_code == 201
    assert upload(client, bundle).status_code == 409
    body = {
        "build": "base",
        "policy": policy.model_dump(),
        "expected_generation": 0,
        "reason": "team review",
    }
    for role in ("reader", "importer"):
        assert (
            client.post(
                base + "/promote", headers=credentials("alpha", role), json=body
            ).status_code
            == 403
        )
    assert (
        client.post(
            base + "/promote", headers=credentials("beta", "approver"), json=body
        ).status_code
        == 404
    )
    assert (
        client.get(base + "/builds/base", headers=credentials("beta", "reader")).status_code == 404
    )
    assert client.get(base + "/builds", headers=credentials("beta", "reader")).json()["items"] == []
    for field in ("tenant", "approved_by", "database"):
        assert (
            client.post(
                base + "/promote",
                headers=credentials("alpha", "approver"),
                json={**body, field: "spoof"},
            ).status_code
            == 422
        )
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: client.post(
                    base + "/promote", headers=credentials("alpha", "approver"), json=body
                ),
                range(2),
            )
        )
    assert sorted(r.status_code for r in responses) == [201, 409]
    event = next(r.json() for r in responses if r.status_code == 201)
    assert event["approval"]["approved_by"] == "alpha.approver"
    for role in ("reader", "approver"):
        assert (
            client.post(
                base + "/comparisons", headers=credentials("alpha", role), json={"build": "base"}
            ).status_code
            == 403
        )
    assert (
        client.post(
            base + "/comparisons", headers=credentials("beta", "importer"), json={"build": "base"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            base + "/comparisons", headers=credentials("alpha", "importer"), json={"build": "base"}
        ).status_code
        == 201
    )
    assert (
        client.get(base + "/comparisons/1", headers=credentials("beta", "reader")).status_code
        == 404
    )
    rollback = {"to_generation": 1, "expected_generation": 1, "reason": "restore"}
    for role in ("reader", "importer"):
        assert (
            client.post(
                base + "/rollback", headers=credentials("alpha", role), json=rollback
            ).status_code
            == 403
        )
    assert (
        client.post(
            base + "/rollback", headers=credentials("beta", "approver"), json=rollback
        ).status_code
        == 409
    )
    assert (
        client.post(
            base + "/rollback", headers=credentials("alpha", "approver"), json=rollback
        ).status_code
        == 201
    )
    restarted = TestClient(create_app(settings))
    assert restarted.get(base, headers=credentials("alpha", "reader")).json()["generation"] == 2
    for route in ("/events", "/comparisons", "/builds"):
        assert (
            restarted.get(base + route, headers=credentials("beta", "reader")).json()["items"] == []
        )
        assert (
            restarted.get(
                base + route + "?limit=51", headers=credentials("alpha", "reader")
            ).status_code
            == 422
        )
    page = restarted.get(base + "/events?limit=1", headers=credentials("alpha", "reader")).json()
    assert page["next_after"] == 1
    assert (
        restarted.get(base + "/events?after=1", headers=credentials("alpha", "reader")).json()[
            "items"
        ][0]["generation"]
        == 2
    )
    assert (
        client.post("/api/v1/runs", headers=credentials("alpha", "approver"), json={}).status_code
        == 403
    )
    assert client.get("/openapi.json").status_code == 200


def test_upload_bounds_and_bad_input(service, bundle, monkeypatch):
    from simweave import catalog_api

    client, _ = service
    headers = {**credentials("alpha", "importer"), "Content-Type": "application/zip"}
    url = "/api/v1/catalog/builds/test"
    assert (
        client.put(url, headers=credentials("alpha", "importer"), content=b"bad").status_code == 415
    )
    assert client.put(url, headers=headers, content=b"bad").status_code == 409
    monkeypatch.setattr(catalog_api, "MAX_TOTAL", 10)
    assert client.put(url, headers=headers, content=iter([b"123456", b"123456"])).status_code == 413
    assert (
        client.get("/api/v1/catalog/builds", headers=credentials("alpha", "reader")).json()["items"]
        == []
    )
    assert (
        client.post("/api/v1/catalog/promote", headers=headers, content=b"x" * 65537).status_code
        == 413
    )


@pytest.mark.parametrize(
    "principal",
    [
        {"tenant": "../escape", "subject": "s", "role": "reader"},
        {"tenant": "alpha", "subject": "s", "role": "admin"},
        {"tenant": "alpha", "subject": "s", "role": "reader", "other": True},
        {"tenant": "alpha", "subject": "\n", "role": "reader"},
    ],
)
def test_invalid_principal(tmp_path, principal):
    with pytest.raises(ValueError):
        Settings(tmp_path / "runs.db", {"x" * 32: principal})


@pytest.mark.parametrize("role", ["reader", "importer", "approver"])
def test_each_role_reads_only_own_catalog(service, bundle, policy, role):
    client, _ = service
    base = "/api/v1/catalog"
    for tenant in ("alpha", "beta"):
        assert upload(client, bundle, tenant=tenant).status_code == 201
        body = {
            "build": "base",
            "policy": policy.model_dump(),
            "expected_generation": 0,
            "reason": tenant + " approval",
        }
        assert (
            client.post(
                base + "/promote", headers=credentials(tenant, "approver"), json=body
            ).status_code
            == 201
        )
        assert (
            client.post(
                base + "/comparisons",
                headers=credentials(tenant, "importer"),
                json={"build": "base"},
            ).status_code
            == 201
        )
    for tenant in ("alpha", "beta"):
        headers = credentials(tenant, role)
        assert client.get(base + "/builds/base", headers=headers).json()["label"] == "base"
        events = client.get(base + "/events", headers=headers).json()["items"]
        assert len(events) == 1
        assert events[0]["approval"]["approved_by"] == tenant + ".approver"
        assert (
            client.get(base + "/comparisons/1", headers=headers).json()["baseline_generation"] == 1
        )
        assert len(client.get(base + "/comparisons", headers=headers).json()["items"]) == 1
        assert client.get(base + "/builds?after=1", headers=headers).json()["items"] == []


def test_archive_nested_input_rejected(tmp_path):
    archive = tmp_path / "deep.ndjson"
    archive.write_bytes(b"[" * 2000 + b"]" * 2000 + b"\n")
    with pytest.raises(ValueError):
        catalog_archive.restore_catalog(archive, tmp_path / "never.db")
    assert not (tmp_path / "never.db").exists()


def test_openapi_binary_contract(service):
    schema = service[0].get("/openapi.json").json()
    route = schema["paths"]["/api/v1/catalog/builds/{label}"]["put"]
    assert route["requestBody"]["content"]["application/zip"]["schema"]["format"] == "binary"
    assert "approved_by" not in schema["components"]["schemas"]["Promote"]["properties"]


def test_numeric_cursors_bounded_before_sql(service):
    client, _ = service
    headers = credentials("alpha", "reader")
    for path in ("builds?after=", "events?after=", "comparisons?after=", "comparisons/"):
        assert (
            client.get(
                "/api/v1/catalog/" + path + "999999999999999999999999", headers=headers
            ).status_code
            == 422
        )


def test_windows_device_tenant_is_portable(tmp_path):
    settings = Settings(
        tmp_path / "runs.db", {"x" * 32: {"tenant": "con", "subject": "reader", "role": "reader"}}
    )
    client = TestClient(create_app(settings))
    assert (
        client.get("/api/v1/catalog", headers={"Authorization": "Bearer " + "x" * 32}).status_code
        == 200
    )
