"""Streaming, seeded execution and telemetry verification without service state."""

from __future__ import annotations

import hashlib
import math
import platform
import random
from collections.abc import Callable, Iterable

from simweave import __version__
from simweave.adapters import Simulator, create_adapter
from simweave.contracts import GateResult, RunResult, Sample, Scenario, canonical


class Measurements:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.count = 0
        self.squared_error = 0.0
        self.max_position = abs(scenario.robot.initial_position)
        self.effort = 0.0
        self.final_error = abs(scenario.controller.target - scenario.robot.initial_position)
        self.digest = hashlib.sha256()

    def add(self, sample: Sample) -> None:
        if sample.step != self.count:
            raise ValueError("telemetry steps must be contiguous from zero")
        if sample.time != sample.step * self.scenario.world.timestep:
            raise ValueError("telemetry time does not match the scenario clock")
        self.digest.update((canonical(sample.model_dump()) + "\n").encode())
        self.max_position = max(self.max_position, abs(sample.position))
        self.final_error = abs(self.scenario.controller.target - sample.position)
        if sample.step:
            self.squared_error += self.final_error**2
            self.effort += abs(sample.control_force) * self.scenario.world.timestep
        self.count += 1

    def finish(self) -> tuple[dict[str, float], list[GateResult]]:
        if self.count != self.scenario.world.steps + 1:
            raise ValueError("telemetry is incomplete or has excess samples")
        metrics = {
            "final_error": self.final_error,
            "rmse": math.sqrt(self.squared_error / self.scenario.world.steps),
            "max_abs_position": self.max_position,
            "control_effort": self.effort,
        }
        gates = [
            GateResult(
                **gate.model_dump(),
                value=metrics[gate.metric],
                passed=(
                    metrics[gate.metric] <= gate.threshold
                    if gate.op == "lte"
                    else metrics[gate.metric] >= gate.threshold
                ),
            )
            for gate in self.scenario.gates
        ]
        return metrics, gates


def execute(
    scenario: Scenario,
    sink: Callable[[Sample], None],
    adapter: Simulator | None = None,
) -> RunResult:
    simulator = adapter if adapter is not None else create_adapter(scenario.adapter)
    rng = random.Random(scenario.seed)
    measurements = Measurements(scenario)

    def emit(sample: Sample) -> None:
        measurements.add(sample)
        sink(sample)

    try:
        x, v = simulator.reset(scenario)
        observed = x + rng.gauss(0, scenario.sensors.position_noise_std)
        emit(
            Sample(
                step=0,
                time=0.0,
                position=x,
                velocity=v,
                observed_position=observed,
                control_force=0.0,
                disturbance_force=0.0,
            )
        )
        c = scenario.controller
        for step in range(scenario.world.steps):
            force = max(-c.max_force, min(c.max_force, c.kp * (c.target - observed) - c.kd * v))
            disturbance = sum(
                d.force
                for d in scenario.disturbances
                if d.start_step <= step < d.start_step + d.duration_steps
            )
            x, v = simulator.step(force + disturbance)
            if not all(math.isfinite(value) and abs(value) < 1e12 for value in (x, v)):
                raise ValueError("simulation diverged")
            observed = x + rng.gauss(0, scenario.sensors.position_noise_std)
            emit(
                Sample(
                    step=step + 1,
                    time=(step + 1) * scenario.world.timestep,
                    position=x,
                    velocity=v,
                    observed_position=observed,
                    control_force=force,
                    disturbance_force=float(disturbance),
                )
            )
        metrics, gates = measurements.finish()
        return RunResult(
            scenario_digest=scenario.digest(),
            telemetry_digest=measurements.digest.hexdigest(),
            adapter=simulator.name,
            adapter_version=simulator.version,
            engine_version=__version__,
            python_version=platform.python_version(),
            sample_count=measurements.count,
            metrics=metrics,
            gates=gates,
            passed=all(g.passed for g in gates),
        )
    finally:
        simulator.close()


def verify_recording(scenario: Scenario, result: RunResult, samples: Iterable[Sample]) -> None:
    """Verify recording integrity and recompute gates. Does not rerun physics."""
    measurements = Measurements(scenario)
    for sample in samples:
        measurements.add(sample)
    metrics, gates = measurements.finish()
    if (
        result.scenario_digest != scenario.digest()
        or result.telemetry_digest != measurements.digest.hexdigest()
        or result.sample_count != measurements.count
        or result.adapter != scenario.adapter
        or result.metrics != metrics
        or result.gates != gates
        or result.passed != all(g.passed for g in gates)
    ):
        raise ValueError("recording integrity check failed")
