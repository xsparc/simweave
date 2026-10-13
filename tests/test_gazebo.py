"""Portable protocol tests. Real physics tests live under integrations/ros2/tests."""

import pytest

from simweave.adapters.gazebo import GazeboSimulator
from simweave.contracts import Scenario
from simweave.engine import execute, verify_recording


class FixtureTransport:
    def __init__(self):
        self.calls, self.closed = [], False
        self.step, self.dt, self.position, self.velocity = 0, 0.01, 0.0, 0.0
        self.fail = None
        self.bad_clock = False

    def call(self, service, fields, timeout):
        self.calls.append((service, fields))
        if service == self.fail:
            raise TimeoutError("synthetic timeout")
        response = {"result": 1}
        if service == "get_simulator_features":
            response["features"] = [20, 25, 26, 31, 32]
        elif service == "configure_cart":
            self.dt = fields["timestep"]
            self.position, self.velocity = fields["initial_position"], fields["initial_velocity"]
            response["adapter_version"] = "test-fixture"
        elif service == "reset_simulation":
            self.step = 0
        elif service == "set_cart_force":
            assert fields["expected_step"] == self.step
        elif service == "step_simulation":
            self.step += fields["steps"]
        elif service == "get_cart_state":
            response.update(
                step=self.step,
                time=self.step * self.dt + int(self.bad_clock),
                position=self.position,
                velocity=self.velocity,
            )
        return response

    def close(self):
        self.closed = True


def test_gazebo_rejects_sub_nanosecond_timestep_before_execution():
    with pytest.raises(ValueError, match="nanoseconds"):
        Scenario.model_validate({"adapter": "gazebo", "world": {"timestep": 0.0010000001}})
    assert Scenario.model_validate({"adapter": "gazebo", "world": {"timestep": 0.0037}})


def test_force_acknowledged_before_step_and_observation():
    transport = FixtureTransport()
    adapter = GazeboSimulator(transport)
    scenario = Scenario.model_validate({"adapter": "gazebo", "world": {"steps": 1}})
    adapter.reset(scenario)
    adapter.step(2.5)
    assert transport.calls[-3:] == [
        ("set_cart_force", {"expected_step": 0, "force": 2.5}),
        ("step_simulation", {"steps": 1}),
        ("get_cart_state", {}),
    ]
    with pytest.raises(RuntimeError, match="horizon"):
        adapter.step(1.0)
    adapter.close()
    adapter.close()
    assert transport.closed


@pytest.mark.parametrize("service", ["set_cart_force", "step_simulation", "get_cart_state"])
def test_uncertain_mutation_is_not_retried(service):
    transport = FixtureTransport()
    adapter = GazeboSimulator(transport)
    adapter.reset(Scenario())
    transport.fail = service
    with pytest.raises(TimeoutError):
        adapter.step(1.0)
    count = len(transport.calls)
    with pytest.raises(RuntimeError, match="not ready"):
        adapter.step(1.0)
    assert len(transport.calls) == count


def test_wrong_native_clock_poisons_adapter():
    transport = FixtureTransport()
    adapter = GazeboSimulator(transport)
    adapter.reset(Scenario())
    transport.bad_clock = True
    with pytest.raises(RuntimeError, match="observation"):
        adapter.step(1.0)
    assert not adapter.ready


def test_gazebo_recording_uses_existing_engine_and_replay_contract():
    scenario = Scenario.model_validate({"adapter": "gazebo", "world": {"steps": 3}})
    samples = []
    transport = FixtureTransport()
    result = execute(scenario, samples.append, GazeboSimulator(transport))
    assert result.adapter == "gazebo"
    assert result.adapter_version == "test-fixture"
    assert not result.passed
    assert transport.closed
    verify_recording(scenario, result, samples)


@pytest.mark.parametrize("force", [float("inf"), float("nan"), 650001.0])
def test_invalid_force_never_reaches_transport(force):
    transport = FixtureTransport()
    adapter = GazeboSimulator(transport)
    adapter.reset(Scenario())
    count = len(transport.calls)
    with pytest.raises(ValueError):
        adapter.step(force)
    assert len(transport.calls) == count


def test_missing_capability_fails_before_configuration():
    class Missing(FixtureTransport):
        def call(self, service, fields, timeout):
            result = super().call(service, fields, timeout)
            if service == "get_simulator_features":
                result["features"] = [20]
            return result

    transport = Missing()
    with pytest.raises(ValueError, match="capabilities"):
        execute(Scenario(), lambda s: None, GazeboSimulator(transport))
    assert [name for name, _ in transport.calls] == ["get_simulator_features"]
    assert transport.closed


def test_rejected_reset_is_not_ready_and_closes_on_execution_failure():
    class Rejected(FixtureTransport):
        def call(self, service, fields, timeout):
            result = super().call(service, fields, timeout)
            if service == "reset_simulation":
                result["result"] = 2
            return result

    transport = Rejected()
    adapter = GazeboSimulator(transport)
    with pytest.raises(RuntimeError, match="rejected"):
        execute(Scenario(), lambda s: None, adapter)
    assert not adapter.ready and transport.closed


@pytest.mark.parametrize(
    "service,respond,requests",
    [
        ("get_simulator_features", True, 2),
        ("get_simulator_features", False, 3),
        ("configure_cart", False, 1),
        ("step_simulation", False, 1),
    ],
)
def test_discovery_query_retry_is_bounded_and_mutations_are_never_retried(
    monkeypatch, service, respond, requests
):
    from types import SimpleNamespace

    from simweave.adapters.gazebo import GazeboTransport

    now = [0.0]
    monkeypatch.setattr("simweave.adapters.gazebo.time.monotonic", lambda: now[0])
    futures = []

    class Future:
        def __init__(self):
            self.cancelled = False
            self.complete = respond and len(futures) > 0

        def done(self):
            return self.complete

        def result(self):
            return SimpleNamespace(features=SimpleNamespace(features=[20, 25]))

        def cancel(self):
            self.cancelled = True

    def call(request):
        future = Future()
        futures.append(future)
        return future

    def spin(node, future, executor, timeout_sec):
        if not future.done():
            now[0] += timeout_sec

    transport = GazeboTransport.__new__(GazeboTransport)
    transport.process = SimpleNamespace(poll=lambda: None)
    transport.node = transport.executor = None
    transport.clients = {
        service: SimpleNamespace(wait_for_service=lambda **k: True, call_async=call)
    }
    transport.types = {service: SimpleNamespace(Request=SimpleNamespace)}
    transport.rclpy = SimpleNamespace(spin_until_future_complete=spin)
    if respond:
        assert transport.call(service, {}, 3)["features"] == [20, 25]
        assert now[0] == 1.0
    else:
        with pytest.raises(TimeoutError):
            transport.call(service, {}, 3)
        assert now[0] == 3.0
    assert len(futures) == requests
    assert all(f.cancelled for f in futures if not f.done())
