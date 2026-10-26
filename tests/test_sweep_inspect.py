"""Workload preview equals admitted expansion without invoking simulators."""

import json

import pytest

from simweave.cli import main
from simweave.sweep_inspect import SweepWorkload, inspect_sweep
from simweave.sweeps import Sweep, plan


def source():
    return Sweep.model_validate(
        {
            "name": "preview",
            "scenario": {"world": {"steps": 10}},
            "axes": [
                {"field": "robot.mass", "values": [1.0, 2.0]},
                {"field": "robot.damping", "values": [0.1, 0.2]},
            ],
            "seeds": [8, 3],
            "adapters": ["reference", "gazebo"],
            "baseline": {},
            "candidate": {"kp": 9.0},
        }
    )


def test_counts_identity_and_order_without_execution(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("preview must not execute")

    monkeypatch.setattr("simweave.suites.execute", denied)
    sweep = source()
    result = inspect_sweep(sweep)
    cases = list(plan(sweep).expand())
    assert result == inspect_sweep(sweep)
    assert result.runs == len(cases) == 32
    assert result.steps == sum(s.world.steps for _, _, s in cases) == 320
    assert result.scenarios == 4
    assert result.suite_digest == plan(sweep).digest()
    assert [p.adapter for p in result.points] == ["reference", "gazebo"] * 4
    assert all(p.seeds == [8, 3] and p.runs == 4 and p.steps == 40 for p in result.points)
    assert [p.parameters["robot.damping"] for p in result.points] == [0.1] * 2 + [0.2] * 2 + [
        0.1
    ] * 2 + [0.2] * 2
    assert SweepWorkload.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("mutation", ["runs", "steps", "mass", "duplicate_seed"])
def test_invalid_plans_never_return_partial_counts(mutation):
    data = source().model_dump()
    if mutation == "runs":
        data["seeds"] = list(range(5))
    elif mutation == "steps":
        data["scenario"]["world"]["steps"] = 20000
    elif mutation == "mass":
        data["axes"][0]["values"] = [-1]
    else:
        data["seeds"] = [1, 1]
    with pytest.raises(ValueError):
        inspect_sweep(Sweep.model_validate(data))


def test_mutated_model_revalidation():
    sweep = source()
    sweep.axes[0].values[0] = -1
    with pytest.raises(ValueError):
        inspect_sweep(sweep)


@pytest.mark.parametrize("version", [True, 1.0, "1", 2])
def test_workload_schema_version_is_strict(version):
    data = inspect_sweep(source()).model_dump()
    data["schema_version"] = version
    with pytest.raises(ValueError):
        SweepWorkload.model_validate(data)


def test_cli_bounds_schema_and_exclusive_output(tmp_path, capsys):
    path = tmp_path / "sweep.json"
    path.write_text(source().model_dump_json(), encoding="utf-8")
    assert main(["sweep-inspect-schema"]) == 0
    assert json.loads(capsys.readouterr().out)["additionalProperties"] is False
    args = ["sweep-inspect", str(path)]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["runs"] == 32
    output = tmp_path / "workload.json"
    assert main(args + ["--output", str(output)]) == 0
    original = output.read_bytes()
    assert main(args + ["--output", str(output)]) == 2
    assert output.read_bytes() == original
    path.write_bytes(b" " * 65537)
    rejected = tmp_path / "rejected.json"
    assert main(args + ["--output", str(rejected)]) == 2
    assert not rejected.exists()
