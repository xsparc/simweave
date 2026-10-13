"""Required live ROS 2 + Gazebo physics conformance. No fake transport or skips."""

import json
import math

import pytest

from simweave.adapters.gazebo import GazeboSimulator, GazeboTransport
from simweave.contracts import Scenario
from simweave.engine import execute, verify_recording


def run(scenario):
    samples = []
    result = execute(scenario, samples.append)
    verify_recording(scenario, result, samples)
    return result, samples


@pytest.mark.parametrize("seed", [7, 42, 99])
def test_repeatability_disturbance_gates_and_mujoco_comparison(seed):
    base = {
        "adapter": "gazebo",
        "seed": seed,
        "sensors": {"position_noise_std": 0.01},
        "disturbances": [{"start_step": 150, "duration_steps": 20, "force": -3.0}],
    }
    scenario = Scenario.model_validate(base)
    first, samples = run(scenario)
    second, repeated = run(scenario)
    assert first.passed and second.passed
    assert samples == repeated
    assert first.telemetry_digest == second.telemetry_digest
    assert "gazebo-" in first.adapter_version
    mujoco, mj_samples = run(Scenario.model_validate({**base, "adapter": "mujoco"}))
    assert mujoco.passed
    # These tolerance budgets apply only to this smooth, contact-free cart fixture.
    assert abs(first.metrics["rmse"] - mujoco.metrics["rmse"]) < 0.02
    assert (
        max(abs(a.position - b.position) for a, b in zip(samples, mj_samples, strict=True)) < 0.03
    )
    assert samples[151].disturbance_force == -3.0


@pytest.mark.parametrize("timestep", [0.001, 0.0037, 0.01, 0.1])
def test_nonzero_initial_conditions_and_first_step_physics(timestep):
    scenario = Scenario.model_validate(
        {
            "adapter": "gazebo",
            "world": {"steps": 2, "timestep": timestep},
            "robot": {
                "mass": 2.0,
                "damping": 0.0,
                "initial_position": -0.5,
                "initial_velocity": 0.3,
            },
            "controller": {"kp": 0.0, "kd": 0.0},
        }
    )
    _, samples = run(scenario)
    assert samples[0].position == -0.5
    assert samples[0].velocity == 0.3
    assert samples[1].position == pytest.approx(-0.5 + 0.3 * timestep, abs=1e-8)
    assert samples[2].velocity == pytest.approx(0.3, abs=1e-8)


def test_reset_and_independent_instances():
    first, second = GazeboSimulator(), GazeboSimulator()
    scenario = Scenario.model_validate({"adapter": "gazebo"})
    try:
        first.reset(scenario)
        second.reset(scenario)
        moved = first.step(10.0)
        assert moved[0] > 0
        assert second.step(0.0) == pytest.approx((0.0, 0.0), abs=1e-10)
        assert first.reset(scenario) == pytest.approx((0.0, 0.0), abs=1e-10)
        assert first.step(10.0) == pytest.approx(moved, abs=1e-10)
    finally:
        first.close()
        second.close()


def test_native_validation_and_stale_force_rejected():
    adapter = GazeboSimulator()
    try:
        adapter.reset(Scenario.model_validate({"adapter": "gazebo"}))
        transport = adapter.transport
        assert (
            transport.call("set_cart_force", {"expected_step": 1, "force": 1.0}, 5)["result"] != 1
        )
        assert (
            transport.call("set_cart_force", {"expected_step": 0, "force": math.nan}, 5)["result"]
            != 1
        )
        assert transport.call("step_simulation", {"steps": 20001}, 5)["result"] != 1
        assert transport.call("reset_simulation", {"scope": 1}, 5)["result"] != 1
        assert transport.call("set_simulation_state", {"state": 1}, 5)["result"] != 1
        assert adapter.step(0.0) == pytest.approx((0.0, 0.0), abs=1e-10)
    finally:
        adapter.close()


def test_fixture_exit_fails_cleanly():
    transport = GazeboTransport()
    try:
        transport.process.kill()
        transport.process.wait(timeout=5)
        with pytest.raises(RuntimeError, match="not running"):
            transport.call("get_simulator_features", {}, 1)
    finally:
        transport.close()


def test_feature_discovery_recovers_a_lost_read_only_response(monkeypatch):
    from rclpy.task import Future

    transport = GazeboTransport()
    try:
        client = transport.clients["get_simulator_features"]
        send = client.call_async
        attempts = []

        def dropped_first_reply(request):
            attempts.append(request)
            return Future() if len(attempts) == 1 else send(request)

        monkeypatch.setattr(client, "call_async", dropped_first_reply)
        result = transport.call("get_simulator_features", {}, 10)
        assert {20, 25, 26, 31, 32} <= set(result["features"])
        assert len(attempts) == 2
    finally:
        transport.close()


def test_unresponsive_fixture_times_out_and_is_reaped():
    import os
    import signal

    adapter = GazeboSimulator()
    try:
        adapter.reset(Scenario.model_validate({"adapter": "gazebo"}))
        process = adapter.transport.process
        os.kill(process.pid, signal.SIGSTOP)
        adapter.timeout = 0.1
        with pytest.raises(TimeoutError):
            adapter.step(1.0)
        assert not adapter.ready
    finally:
        adapter.close()
    assert process.poll() is not None


def test_native_child_stops_when_experiment_owner_is_killed():
    import select
    import subprocess
    import sys
    import time
    from pathlib import Path

    code = (
        "from simweave.adapters.gazebo import GazeboTransport; import time; "
        "t=GazeboTransport(); t.call('get_simulator_features', {}, 10); "
        "print(t.process.pid, flush=True); time.sleep(60)"
    )
    owner = subprocess.Popen(
        [sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    try:
        assert select.select([owner.stdout], [], [], 20)[0], "owner did not start fixture"
        pid = int(owner.stdout.readline())
        owner.kill()
        owner.wait(timeout=5)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            state = Path(f"/proc/{pid}/stat")
            if not state.exists() or state.read_text().split(") ", 1)[1].startswith("Z"):
                break  # Exited; PID 1 may not have reaped the orphan yet.
            time.sleep(0.1)
        else:
            pytest.fail("native fixture survived owner death")
    finally:
        if owner.poll() is None:
            owner.kill()
        owner.wait(timeout=5)
        owner.stdout.close()


def test_generic_lifecycle_bridge_uses_its_own_ros_context():
    from simweave.adapters.ros2 import RclpyTransport, RosControl

    adapter = GazeboSimulator()
    try:
        scenario = Scenario.model_validate({"adapter": "gazebo"})
        adapter.reset(scenario)
        transport = RclpyTransport(adapter.transport.node.get_namespace())
        try:
            control = RosControl(transport)
            assert {20, 25, 26, 31, 32} <= control.features()
            control.step(2)
            state = adapter.transport.call("get_cart_state", {}, 5)
            assert state["step"] == 2
            control.reset()
            state = adapter.transport.call("get_cart_state", {}, 5)
            assert state["step"] == 0 and state["time"] == 0
        finally:
            transport.close()
    finally:
        adapter.close()


def test_cli_recording_and_offline_replay(tmp_path):
    from simweave.cli import main

    scenario = tmp_path / "scenario.json"
    scenario.write_text(
        json.dumps(
            {
                "adapter": "gazebo",
                "world": {"steps": 20},
                "gates": [{"metric": "max_abs_position", "threshold": 10.0}],
            }
        )
    )
    output = tmp_path / "recording"
    assert main(["run", str(scenario), "--output", str(output)]) == 0
    assert main(["replay", str(output)]) == 0


def test_api_worker_gates_export_and_offline_replay(tmp_path):
    from fastapi.testclient import TestClient

    from simweave.api import create_app
    from simweave.cli import main
    from simweave.config import Settings
    from simweave.worker import work_once

    token = "synthetic-gazebo-test-token-0000000000000"
    app = create_app(Settings(tmp_path / "runs.sqlite3", {token: "cart-test"}))
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        capabilities = client.get("/api/v1/capabilities", headers=headers).json()
        assert next(a for a in capabilities["adapters"] if a["id"] == "gazebo")["available"]
        response = client.post(
            "/api/v1/runs",
            headers=headers,
            json={
                "adapter": "gazebo",
                "world": {"steps": 10},
                "gates": [{"metric": "final_error", "threshold": 0.0}],
            },
        )
        assert response.status_code == 202
        identifier = response.json()["id"]
        assert work_once(app.state.store)
        run = client.get(f"/api/v1/runs/{identifier}", headers=headers).json()
        assert run["status"] == "succeeded", run
        assert run["result"]["passed"] is False
        assert client.post(f"/api/v1/runs/{identifier}/verify", headers=headers).json()["verified"]
        exported = client.get(f"/api/v1/runs/{identifier}/recording", headers=headers)
        recording = tmp_path / "export.jsonl"
        recording.write_text(exported.text)
        assert main(["replay", str(recording)]) == 1  # Valid recording; failed quality gate.
