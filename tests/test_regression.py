import json
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from simweave.api import create_app
from simweave.cli import main
from simweave.comparison import RunSummary, compare, preview
from simweave.config import Settings
from simweave.contracts import Scenario
from simweave.engine import execute
from simweave.suites import Suite, SuiteReport, execute_suite, review
from simweave.worker import work_once


def contract(**overrides):
    return Suite.model_validate(
        {
            "name": "Recovery",
            "scenarios": [{"name": "Cart"}],
            "adapters": ["reference"],
            "seeds": [1, 2],
            "baseline": {},
            "candidate": {},
            "regression_gates": [{"metric": "rmse", "max_increase": 0.02}],
            **overrides,
        }
    )


def summary(data=None):
    scenario = Scenario.model_validate(data or {})
    samples = []
    result = execute(scenario, samples.append)
    return RunSummary(scenario=scenario, result=result, trajectory=preview(scenario, samples))


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": True},
        {"name": "Invalid\u0000XML"},
        {"unknown": 1},
        {"seeds": [1, 1]},
        {"seeds": [True]},
        {"adapters": ["reference", "reference"]},
        {"adapters": ["shell"]},
        {"scenarios": [{"name": "same"}, {"name": "same"}]},
        {"candidate": {"target": 2.0}},
        {"regression_gates": [{"metric": "rmse", "max_increase": -1.0}]},
        {"regression_gates": [{"metric": "rmse", "max_increase": 0.1}] * 2},
        {"adapters": ["reference", "mujoco", "gazebo"], "seeds": list(range(11))},
        {"scenarios": [{"world": {"steps": 20000}}], "seeds": list(range(6))},
        {"scenarios": [{"world": {"timestep": 0.00100000001}}], "adapters": ["gazebo"]},
    ],
)
def test_suite_rejects_invalid_or_unbounded_work(change):
    with pytest.raises(ValidationError):
        contract(**change)


def test_matrix_expansion_and_seed_controller_overrides():
    suite = contract(adapters=["reference", "mujoco"], seeds=list(range(10)))
    cases = list(suite.expand())
    assert len(cases) == 40
    assert len({identifier for identifier, _, _ in cases}) == 40
    assert [(role, s.seed, s.adapter) for _, role, s in cases[:4]] == [
        ("baseline", 0, "reference"),
        ("candidate", 0, "reference"),
        ("baseline", 1, "reference"),
        ("candidate", 1, "reference"),
    ]


@pytest.mark.parametrize("candidate,expected", [({}, 0), ({"kp": 0.0, "kd": 0.0}, 1)])
def test_cli_reports_replay_and_junit_with_real_gate_failure(tmp_path, candidate, expected):
    suite = contract(candidate=candidate)
    source, output = tmp_path / "suite.json", tmp_path / "results"
    source.write_text(suite.model_dump_json())
    assert main(["suite", str(source), "--output", str(output)]) == expected
    report = SuiteReport.model_validate_json((output / "report.json").read_bytes())
    result = review(report)
    assert result.exit_code == expected
    assert len(result.pairs) == 2
    assert len(result.pairs[0].comparison.baseline.trajectory) == 101
    assert result.pairs[0].comparison.newly_failing_gates == ([0] if expected else [])
    assert main(["replay", str(output / "case-0000")]) == 0
    assert main(["replay", str(output / "case-0001")]) == expected
    xml = ET.parse(output / "junit.xml").getroot()
    assert int(xml.get("tests")) == 6  # Four runs and two regression checks.
    assert int(xml.get("failures")) == (4 if expected else 0)
    assert xml.get("errors") == "0"
    assert main(["suite", str(source), "--output", str(output)]) == 2


@pytest.mark.parametrize(
    "failure,category", [(ImportError, "adapter_unavailable"), (OSError, "execution_failed")]
)
def test_execution_errors_continue_and_are_not_skipped(tmp_path, monkeypatch, failure, category):
    real_execute = execute

    def sometimes(scenario, sink):
        if scenario.seed == 1:
            raise failure("private synthetic diagnostic")
        return real_execute(scenario, sink)

    monkeypatch.setattr("simweave.suites.execute", sometimes)
    report = execute_suite(contract(), tmp_path / "out")
    assert review(report).exit_code == 2
    assert [c.error for c in report.cases] == [category] * 2 + [None] * 2
    assert "private" not in report.model_dump_json()
    root = ET.parse(tmp_path / "out/junit.xml").getroot()
    assert root.get("errors") == "2"


def test_baseline_failure_alone_fails_the_suite(tmp_path):
    report = execute_suite(contract(baseline={"kp": 0.0, "kd": 0.0}), tmp_path / "out")
    pair = review(report).pairs[0].comparison
    assert not pair.passed
    assert pair.candidate.result.passed
    assert "Baseline" in pair.warnings[0]


@pytest.mark.parametrize(
    "change",
    [
        {"seed": 99},
        {"world": {"steps": 599}},
        {"robot": {"mass": 2.0}},
        {"sensors": {"position_noise_std": 0.1}},
        {"controller": {"target": 2.0}},
        {"gates": [{"metric": "rmse", "threshold": 1.0}]},
    ],
)
def test_confounded_pairs_are_rejected(change):
    with pytest.raises(ValueError, match="matching inputs"):
        compare(summary(), summary(change))


def test_metric_delta_and_runtime_warning():
    a, b = summary(), summary({"controller": {"kp": 0.0}})
    b = b.model_copy(update={"result": b.result.model_copy(update={"engine_version": "other"})})
    data = compare(a, b)
    delta = next(m for m in data.metrics if m.metric == "final_error")
    assert delta.delta == b.result.metrics["final_error"] - a.result.metrics["final_error"]
    assert "Runtime versions differ" in data.warnings[0]


@pytest.mark.parametrize(
    "field",
    ["suite_digest", "case_count", "case_order", "metrics", "gates", "trajectory", "version"],
)
def test_imported_reports_reject_inconsistent_data(tmp_path, field):
    data = execute_suite(contract(seeds=[1]), tmp_path / "out").model_dump()
    if field == "suite_digest":
        data["suite_digest"] = "0" * 64
    if field == "case_count":
        data["cases"].pop()
    if field == "case_order":
        data["cases"].reverse()
    if field == "metrics":
        data["cases"][0]["summary"]["result"]["metrics"] = {}
    if field == "gates":
        data["cases"][0]["summary"]["result"]["gates"][0]["value"] = 1.0
    if field == "trajectory":
        data["cases"][0]["summary"]["trajectory"].pop()
    if field == "version":
        data["schema_version"] = True
    with pytest.raises(ValueError):
        SuiteReport.model_validate(data)


def test_authenticated_comparison_and_report_import(tmp_path):
    token, other = "a" * 40, "b" * 40
    auth = {"Authorization": f"Bearer {token}"}
    app = create_app(Settings(tmp_path / "db", {token: "alpha", other: "beta"}))
    with TestClient(app) as client:
        ids = []
        for controller in ({}, {"kp": 0.0, "kd": 0.0}):
            ids.append(
                client.post("/api/v1/runs", json={"controller": controller}, headers=auth).json()[
                    "id"
                ]
            )
        url = f"/api/v1/comparisons?baseline={ids[0]}&candidate={ids[1]}"
        assert client.get(url).status_code == 401
        assert client.get(url, headers=auth).status_code == 409
        assert work_once(app.state.store) and work_once(app.state.store)
        data = client.get(url, headers=auth)
        assert data.status_code == 200, data.text
        assert data.json()["newly_failing_gates"] == [0]
        assert len(data.json()["baseline"]["trajectory"]) == 101
        beta = {"Authorization": f"Bearer {other}"}
        assert client.get(url, headers=beta).status_code == 404
        beta_id = client.post("/api/v1/runs", json={}, headers=beta).json()["id"]
        assert client.get(url.replace(ids[1], beta_id), headers=auth).status_code == 404
        report = execute_suite(contract(), tmp_path / "out")
        endpoint = "/api/v1/suite-reports/compare"
        assert client.post(endpoint, json=report.model_dump()).status_code == 401
        imported = client.post(endpoint, json=report.model_dump(), headers=auth)
        assert imported.status_code == 200, imported.text
        assert imported.json()["exit_code"] == 0
        assert len(app.state.store.list("alpha")) == 2  # Import creates no runs.
        assert (
            client.post(endpoint, content="x" * (4 * 1024 * 1024 + 1), headers=auth).status_code
            == 413
        )
        with app.state.store.connect() as db:
            db.execute("DELETE FROM samples WHERE run_id=? AND step=2", (ids[0],))
        assert client.get(url, headers=auth).status_code == 409


def test_suite_schema_command(capsys):
    assert main(["suite-schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["additionalProperties"] is False
