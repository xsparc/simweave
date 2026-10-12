import pytest

from simweave.adapters.ros2 import RosControl
from simweave.contracts import Scenario
from simweave.engine import execute


def test_real_mujoco_reset_and_repeatability():
    pytest.importorskip("mujoco")
    from simweave.adapters.mujoco import MujocoSimulator

    scenario = Scenario.model_validate(
        {"adapter": "mujoco", "sensors": {"position_noise_std": 0.01}}
    )
    adapter = MujocoSimulator()
    first, second = [], []
    a = execute(scenario, first.append, adapter)
    b = execute(scenario, second.append, adapter)
    assert a == b
    assert first == second
    assert a.passed
    assert a.adapter_version != "1"
    assert len(first) == scenario.world.steps + 1


class FakeRos:
    def __init__(self, features=(20, 21, 22, 23, 25, 26, 31, 32), result=1):
        self.supported = features
        self.result = result
        self.calls = []

    def call(self, service, fields, timeout):
        self.calls.append((service, fields))
        return (
            {"features": self.supported}
            if service == "get_simulator_features"
            else {"result": self.result}
        )


def test_ros_capability_checked_reset_pause_and_step():
    transport = FakeRos()
    control = RosControl(transport)
    control.reset()
    control.step(3)
    assert transport.calls == [
        ("get_simulator_features", {}),
        ("reset_simulation", {"scope": 255}),
        ("get_simulator_features", {}),
        ("set_simulation_state", {"state": 2}),
        ("step_simulation", {"steps": 3}),
    ]


def test_ros_missing_capability_fails_before_mutation():
    transport = FakeRos(features=(31, 32))
    with pytest.raises(ValueError):
        RosControl(transport).step()
    assert len(transport.calls) == 1


def test_ros_rejection_does_not_step():
    transport = FakeRos(result=4)
    with pytest.raises(RuntimeError):
        RosControl(transport).step()
    assert all(call[0] != "step_simulation" for call in transport.calls)


def test_ros_already_paused_is_success():
    class AlreadyPaused(FakeRos):
        def call(self, service, fields, timeout):
            response = super().call(service, fields, timeout)
            return {"result": 101} if service == "set_simulation_state" else response

    transport = AlreadyPaused()
    RosControl(transport).step()
    assert transport.calls[-1] == ("step_simulation", {"steps": 1})


@pytest.mark.parametrize("steps", [0, 20001, True, 1.2])
def test_ros_invalid_steps(steps):
    with pytest.raises(ValueError):
        RosControl(FakeRos()).step(steps)
