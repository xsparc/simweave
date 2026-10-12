"""Versioned, closed scenario contracts. All physical units are SI."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Number = Annotated[float, Field(allow_inf_nan=False)]
MetricName = Literal["final_error", "rmse", "max_abs_position", "control_effort"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class World(Contract):
    timestep: Number = Field(default=0.01, ge=0.001, le=0.1)
    steps: int = Field(default=600, ge=1, le=20_000)


class Robot(Contract):
    kind: Literal["cart_1d"] = "cart_1d"
    mass: Number = Field(default=1.0, ge=0.1, le=1000)
    damping: Number = Field(default=0.2, ge=0, le=10)
    initial_position: Number = Field(default=0.0, ge=-100, le=100)
    initial_velocity: Number = Field(default=0.0, ge=-100, le=100)


class Controller(Contract):
    kind: Literal["pd"] = "pd"
    target: Number = Field(default=1.0, ge=-100, le=100)
    kp: Number = Field(default=8.0, ge=0, le=1000)
    kd: Number = Field(default=4.0, ge=0, le=1000)
    max_force: Number = Field(default=20.0, gt=0, le=10_000)


class Sensors(Contract):
    position_noise_std: Number = Field(default=0.0, ge=0, le=10)


class Disturbance(Contract):
    start_step: int = Field(ge=0, lt=20_000)
    duration_steps: int = Field(ge=1, le=20_000)
    force: Number = Field(ge=-10_000, le=10_000)


class Gate(Contract):
    metric: MetricName
    op: Literal["lte", "gte"] = "lte"
    threshold: Number = Field(ge=0)


class Scenario(Contract):
    schema_version: Literal[1] = 1
    name: str = Field(default="Cart disturbance recovery", min_length=1, max_length=100)
    adapter: Literal["reference", "mujoco"] = "reference"
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    world: World = Field(default_factory=World)
    robot: Robot = Field(default_factory=Robot)
    controller: Controller = Field(default_factory=Controller)
    sensors: Sensors = Field(default_factory=Sensors)
    disturbances: list[Disturbance] = Field(default_factory=list, max_length=64)
    gates: list[Gate] = Field(
        default_factory=lambda: [Gate(metric="final_error", threshold=0.05)],
        min_length=1,
        max_length=16,
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @model_validator(mode="after")
    def validate_horizon(self) -> Scenario:
        for disturbance in self.disturbances:
            if disturbance.start_step + disturbance.duration_steps > self.world.steps:
                raise ValueError("disturbance extends beyond the simulation horizon")
        return self

    def digest(self) -> str:
        return hashlib.sha256(canonical(self.model_dump()).encode()).hexdigest()


class Sample(Contract):
    step: int = Field(ge=0)
    time: Number = Field(ge=0)
    position: Number
    velocity: Number
    observed_position: Number
    control_force: Number
    disturbance_force: Number


class GateResult(Contract):
    metric: MetricName
    op: Literal["lte", "gte"]
    threshold: Number
    value: Number
    passed: bool


class RunResult(Contract):
    schema_version: Literal[1] = 1
    scenario_digest: str
    telemetry_digest: str
    adapter: str
    adapter_version: str
    engine_version: str
    python_version: str
    sample_count: int
    metrics: dict[str, Number]
    gates: list[GateResult]
    passed: bool


class RunView(Contract):
    id: str
    scenario: Scenario
    scenario_digest: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    created_at: Number
    updated_at: Number
    result: RunResult | None
    error: str | None


class RunsPage(Contract):
    items: list[RunView]
    next_before: str | None


class TelemetryPage(Contract):
    items: list[Sample]
    next_after: int | None


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
