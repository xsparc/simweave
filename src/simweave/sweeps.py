"""Deterministic, plan-only parameter expansion into the existing Suite contract."""

from itertools import product
from math import prod
from typing import Literal

from pydantic import Field, field_validator, model_validator

from simweave.comparison import RegressionGate
from simweave.contracts import Contract, Controller, Number, Scenario
from simweave.suites import Adapter, Seed, Suite


class Axis(Contract):
    field: Literal[
        "robot.mass",
        "robot.damping",
        "robot.initial_position",
        "robot.initial_velocity",
        "sensors.position_noise_std",
    ]
    values: list[Number] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def unique_values(self):
        if len(set(self.values)) != len(self.values):
            raise ValueError("axis values must be unique")
        return self


class Sweep(Contract):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=100)
    scenario: Scenario
    axes: list[Axis] = Field(min_length=1, max_length=3)
    seeds: list[Seed] = Field(min_length=1, max_length=32)
    adapters: list[Adapter] = Field(min_length=1, max_length=3)
    baseline: Controller
    candidate: Controller
    regression_gates: list[RegressionGate] = Field(default_factory=list, max_length=4)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @model_validator(mode="after")
    def bounded_axes(self):
        if len({axis.field for axis in self.axes}) != len(self.axes):
            raise ValueError("axis fields must be unique")
        if prod(len(axis.values) for axis in self.axes) > 8:
            raise ValueError("sweep exceeds eight scenarios")
        return self


def plan(sweep: Sweep) -> Suite:
    """Revalidate even mutated models; validate all cases before returning a plan."""
    sweep = Sweep.model_validate(sweep.model_dump())
    scenarios = []
    for index, values in enumerate(product(*(axis.values for axis in sweep.axes)), start=1):
        data = sweep.scenario.model_dump()
        data["name"] = f"{sweep.scenario.name[:89]} [sweep-{index:02d}]"
        for axis, value in zip(sweep.axes, values, strict=True):
            # Both keys come from the closed Literal above, never an arbitrary path.
            section, field = axis.field.split(".")
            data[section][field] = value
        scenarios.append(Scenario.model_validate(data))
    return Suite(
        name=sweep.name,
        scenarios=scenarios,
        seeds=sweep.seeds,
        adapters=sweep.adapters,
        baseline=sweep.baseline,
        candidate=sweep.candidate,
        regression_gates=sweep.regression_gates,
    )
