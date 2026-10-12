import json

import pytest
from pydantic import ValidationError

from simweave.adapters.reference import ReferenceSimulator
from simweave.cli import main
from simweave.contracts import Scenario
from simweave.engine import execute, verify_recording


def run(scenario):
    samples = []
    return execute(scenario, samples.append), samples


@pytest.mark.parametrize(
    "change",
    [
        {"seed": True},
        {"seed": -1},
        {"seed": "42"},
        {"schema_version": 2},
        {"surprise": 1},
        {"adapter": "shell"},
        {"world": {"steps": 20001}},
        {"world": {"steps": 0}},
        {"world": {"timestep": float("nan")}},
        {"robot": {"mass": 0}},
        {"gates": []},
        {"controller": {"kp": "8"}},
        {"disturbances": [{"start_step": 590, "duration_steps": 20, "force": 1.0}]},
    ],
)
def test_rejects_invalid_contracts(change):
    with pytest.raises(ValidationError):
        Scenario.model_validate(change)


def test_seeded_replay_and_digest():
    scenario = Scenario.model_validate({"sensors": {"position_noise_std": 0.02}})
    result, samples = run(scenario)
    second, repeated = run(scenario)
    assert result == second
    assert samples == repeated
    assert result.passed
    verify_recording(scenario, result, iter(samples))
    changed, _ = run(scenario.model_copy(update={"seed": 43}))
    assert changed.telemetry_digest != result.telemetry_digest


def test_normalized_contract_digest():
    assert (
        Scenario().digest() == Scenario.model_validate_json(Scenario().model_dump_json()).digest()
    )


@pytest.mark.parametrize("corruption", ["truncate", "duplicate", "position", "clock", "gate"])
def test_replay_rejects_corruption(corruption):
    scenario = Scenario()
    result, samples = run(scenario)
    if corruption == "truncate":
        samples.pop()
    elif corruption == "duplicate":
        samples[1] = samples[0]
    elif corruption == "position":
        samples[1] = samples[1].model_copy(update={"position": 100.0})
    elif corruption == "clock":
        samples[1] = samples[1].model_copy(update={"time": 99.0})
    else:
        result = result.model_copy(update={"passed": False})
    with pytest.raises(ValueError):
        verify_recording(scenario, result, samples)


def test_disturbance_timing_and_gate_failure():
    scenario = Scenario.model_validate(
        {
            "world": {"steps": 3},
            "controller": {"kp": 0.0, "kd": 0.0},
            "disturbances": [{"start_step": 1, "duration_steps": 1, "force": 2.0}],
        }
    )
    result, samples = run(scenario)
    assert [s.disturbance_force for s in samples] == [0, 0, 2, 0]
    assert not result.passed


def test_adapter_closed_when_sink_fails():
    class Tracked(ReferenceSimulator):
        closed = False

        def close(self):
            self.closed = True

    adapter = Tracked()

    def fail(sample):
        raise RuntimeError("synthetic sink failure")

    with pytest.raises(RuntimeError):
        execute(Scenario(), fail, adapter)
    assert adapter.closed


def test_cli_round_trip_and_overwrite_protection(tmp_path, capsys):
    scenario = tmp_path / "scenario.json"
    output = tmp_path / "run"
    assert main(["init", str(scenario)]) == 0
    assert main(["validate", str(scenario)]) == 0
    assert main(["run", str(scenario), "--output", str(output)]) == 0
    assert main(["replay", str(output)]) == 0
    assert main(["run", str(scenario), "--output", str(output)]) == 2
    assert json.loads((output / "result.json").read_text())["passed"]
