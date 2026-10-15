"""100 authenticated review flows and coordinated 1,000-bundle recovery drill."""

import argparse
import json
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from simweave.api import create_app
from simweave.config import Settings
from simweave.observability import snapshot
from simweave.recovery import checkpoint, restore
from simweave.suite_jobs import work_once
from simweave.suites import Suite, execute_suite


def contract(index):
    return Suite.model_validate(
        {
            "name": f"flow-{index}",
            "scenarios": [
                {
                    "name": "cart",
                    "world": {"steps": 5},
                    "gates": [{"metric": "rmse", "threshold": 10.0}],
                }
            ],
            "seeds": [1],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {},
        }
    )


def token(tenant, role):
    return (tenant + "-" + role).ljust(32, "x")


def headers(tenant, role):
    return {"Authorization": "Bearer " + token(tenant, role)}


def settings(root, backend=None):
    tokens = {}
    for tenant in ("alpha", "beta"):
        tokens[token(tenant, "run")] = tenant
        for role in ("reader", "importer", "approver"):
            tokens[token(tenant, role)] = {"tenant": tenant, "subject": role, "role": role}
    return Settings(root / "runs.sqlite3", tokens, artifact_backend=backend)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--backend", type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    tempfile.tempdir = str(root)
    app = create_app(settings(root / "source", args.backend))
    items = []
    with TestClient(app) as client:
        for i in range(100):
            tenant, other = ("alpha", "beta") if i % 2 == 0 else ("beta", "alpha")
            response = client.post(
                "/api/v1/suite-jobs",
                json=contract(i).model_dump(),
                headers={**headers(tenant, "run"), "Idempotency-Key": f"job-{i}"},
            )
            assert response.status_code == 202
            job = response.json()["id"]
            assert work_once(app.state.suite_jobs, app.state.artifacts)
            assert app.state.suite_jobs.get(tenant, job)["status"] == "succeeded"
            if i < 2:
                assert (
                    client.post(
                        "/api/v1/catalog/builds/baseline/from-job",
                        json={"job": job, "role": "baseline"},
                        headers=headers(tenant, "importer"),
                    ).status_code
                    == 201
                )
                assert (
                    client.post(
                        "/api/v1/catalog/promote",
                        json={
                            "build": "baseline",
                            "policy": {
                                "metrics": [{"metric": "rmse", "max_increase": 0.1}],
                                "resamples": 1000,
                            },
                            "expected_generation": 0,
                            "reason": "synthetic drill",
                        },
                        headers=headers(tenant, "approver"),
                    ).status_code
                    == 201
                )
            label = f"candidate-{i}"
            route = f"/api/v1/catalog/builds/{label}/from-job"
            assert (
                client.post(
                    route, json={"job": job}, headers=headers(other, "importer")
                ).status_code
                == 404
            )
            assert (
                client.post(
                    route, json={"job": job}, headers=headers(tenant, "importer")
                ).status_code
                == 201
            )
            comparison = client.post(
                "/api/v1/catalog/comparisons",
                json={"build": label},
                headers=headers(tenant, "importer"),
            )
            assert comparison.status_code == 201, comparison.text
            download = f"/api/v1/catalog/builds/{label}/artifact"
            evidence = client.get(download, headers=headers(tenant, "reader"))
            assert evidence.status_code == 200 and evidence.content[:2] == b"PK"
            assert client.get(download, headers=headers(other, "reader")).status_code == 404
            assert (
                client.get(
                    f"/api/v1/suite-jobs/{job}/artifact", headers=headers(tenant, "run")
                ).content
                == evidence.content
            )
            items.append((tenant, job, label))
    for i in range(100, 1000):
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            output = Path(temporary) / "suite"
            execute_suite(contract(i), output)
            app.state.artifacts.put("alpha" if i % 2 == 0 else "beta", output / "evidence.zip")
    assert (
        snapshot(app.state.suite_jobs, app.state.artifacts)["metrics"][
            "simweave_artifacts_retained"
        ]
        == 1000
    )
    # TestClient is closed, all workers are finished: a coordinated quiescent boundary.
    started = time.monotonic()
    saved = checkpoint(
        app.state.suite_jobs,
        app.state.artifacts,
        root / "source/runs.sqlite3.catalogs",
        root / "checkpoint",
    )
    restored = restore(root / "checkpoint", root / "restored")
    seconds = time.monotonic() - started
    assert seconds < 300 and saved["jobs"] == restored["jobs"] == 100
    assert saved["artifacts"] == restored["artifacts"] == 1000
    recovered = create_app(settings(root / "restored"))
    with TestClient(recovered) as client:
        for tenant, job, label in items:
            assert recovered.state.suite_jobs.get(tenant, job)["status"] == "succeeded"
            assert (
                client.get(
                    f"/api/v1/catalog/builds/{label}/artifact", headers=headers(tenant, "reader")
                ).status_code
                == 200
            )
        for tenant in ("alpha", "beta"):
            assert (
                len(
                    client.get(
                        "/api/v1/catalog/comparisons?limit=50", headers=headers(tenant, "reader")
                    ).json()["items"]
                )
                == 50
            )
    result = {
        "schema_version": 1,
        "review_flows": 100,
        "tenants": 2,
        "recovered_jobs": 100,
        "recovered_artifacts": 1000,
        "missing_references": 0,
        "cross_tenant_reads": 0,
        "recovery_seconds": round(seconds, 3),
    }
    (root / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
