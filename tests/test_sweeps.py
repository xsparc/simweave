"""Sweep admission, deterministic expansion and actual existing Suite execution."""

import json

import pytest
from pydantic import ValidationError

from simweave.cli import main
from simweave.suites import Suite, execute_suite
from simweave.sweeps import Sweep, plan


def spec():
    return {
        "schema_version": 1,
        "name": "Mass and damping",
        "scenario": {"name": "Cart", "world": {"steps": 10}},
        "axes": [
            {"field": "robot.mass", "values": [1.0, 2.0]},
            {"field": "robot.damping", "values": [0.1, 0.3]},
        ],
        "seeds": [7, 3],
        "adapters": ["reference"],
        "baseline": {},
        "candidate": {"kp": 9.0},
    }


def test_deterministic_order_independent_scenarios_and_execution(tmp_path):
    source = Sweep.model_validate(spec())
    suite = plan(source)
    assert suite.digest() == plan(source).digest()
    assert [(s.robot.mass, s.robot.damping) for s in suite.scenarios] == [
        (1.0, 0.1),
        (1.0, 0.3),
        (2.0, 0.1),
        (2.0, 0.3),
    ]
    assert suite.scenarios[0].name == "Cart [sweep-01]"
    assert suite.scenarios[-1].name == "Cart [sweep-04]"
    assert source.scenario.robot.damping == 0.2
    assert len(list(suite.expand())) == 16
    report = execute_suite(suite, tmp_path / "bundle")
    assert len(report.cases) == 16
    assert all(case.error is None for case in report.cases)
    assert report.suite_digest == suite.digest()


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": True},
        {"schema_version": 2},
        {"extra": True},
        {"axes": []},
        {"axes": [{"field": "robot.__class__", "values": [1.0]}]},
        {"axes": [{"field": "robot.mass", "values": [float("nan")]}]},
        {"axes": [{"field": "robot.mass", "values": [True]}]},
        {"axes": [{"field": "robot.mass", "values": [1.0, 1.0]}]},
        {"axes": [{"field": "robot.mass", "values": [0.0]}]},
        {"axes": [{"field": "sensors.position_noise_std", "values": [-1.0]}]},
        {"axes": [{"field": "robot.mass", "values": [1.0]}] * 2},
        {
            "axes": [
                {"field": "robot.mass", "values": [1.0, 2.0, 3.0]},
                {"field": "robot.damping", "values": [0.1, 0.2, 0.3]},
            ]
        },
        {"seeds": list(range(9))},  # 4 * 9 * 2 > 64
        {"seeds": [1, 1]},
        {"scenario": {"world": {"steps": 20000}}},  # 320000 steps
        {"baseline": {"target": 2.0}},
    ],
)
def test_invalid_sweeps_fail_before_execution(change):
    data = spec() | change
    with pytest.raises((ValueError, ValidationError)):
        plan(Sweep.model_validate(data))


def test_mutated_contract_revalidated_and_names_bounded():
    source = Sweep.model_validate(spec() | {"scenario": {"name": "x" * 100}})
    assert all(len(s.name) == 100 for s in plan(source).scenarios)
    source.axes[0].values.append(1.0)
    with pytest.raises(ValueError):
        plan(source)


def test_cli_json_schema_stdout_file_and_rejection(tmp_path, capsys):
    path = tmp_path / "sweep.json"
    path.write_text(json.dumps(spec()), encoding="utf-8")
    assert main(["sweep-schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["additionalProperties"] is False
    assert main(["sweep", str(path)]) == 0
    suite = Suite.model_validate_json(capsys.readouterr().out)
    output = tmp_path / "suite.json"
    assert main(["sweep", str(path), "--output", str(output)]) == 0
    original = output.read_bytes()
    assert Suite.model_validate_json(original).digest() == suite.digest()
    assert main(["sweep", str(path), "--output", str(output)]) == 2
    assert output.read_bytes() == original
    path.write_text(json.dumps(spec() | {"seeds": list(range(9))}), encoding="utf-8")
    rejected = tmp_path / "invalid.json"
    assert main(["sweep", str(path), "--output", str(rejected)]) == 2
    assert not rejected.exists()
    path.write_bytes(b" " * 65537)
    assert main(["sweep", str(path)]) == 2
    assert capsys.readouterr().out == ""


def test_generated_sweep_runs_with_installed_mujoco(tmp_path):
    pytest.importorskip("mujoco")
    source = Sweep.model_validate(spec() | {"adapters": ["mujoco"], "seeds": [1]})
    report = execute_suite(plan(source), tmp_path / "mujoco-bundle")
    assert len(report.cases) == 8
    assert all(case.error is None for case in report.cases)
