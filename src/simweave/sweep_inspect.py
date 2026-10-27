"""Plan-only workload counts derived from the admitted Suite expansion."""

import hashlib
from typing import Literal

from pydantic import Field, field_validator

from simweave.contracts import Contract, Number, canonical
from simweave.suites import MAX_SUITE_RUNS, MAX_SUITE_STEPS, Adapter, Seed
from simweave.sweeps import Sweep, plan


class PointWorkload(Contract):
    scenario: str
    parameters: dict[str, Number]
    adapter: Adapter
    seeds: list[Seed]
    runs: int = Field(ge=2, le=MAX_SUITE_RUNS)
    steps: int = Field(ge=1, le=MAX_SUITE_STEPS)


class SweepWorkload(Contract):
    schema_version: Literal[1] = 1
    sweep_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    suite_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    scenarios: int = Field(ge=1, le=8)
    runs: int = Field(ge=2, le=MAX_SUITE_RUNS)
    steps: int = Field(ge=1, le=MAX_SUITE_STEPS)
    points: list[PointWorkload] = Field(min_length=1, max_length=24)
    interpretation: Literal["planned_counts_not_runtime_estimates"] = (
        "planned_counts_not_runtime_estimates"
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value


def inspect_sweep(sweep: Sweep) -> SweepWorkload:
    """Fully validate admission before returning counts; never load an adapter."""
    sweep = Sweep.model_validate(sweep.model_dump())
    suite = plan(sweep)
    cases = list(suite.expand())
    points = []
    for scenario in suite.scenarios:
        data = scenario.model_dump()
        parameters = {}
        for axis in sweep.axes:
            section, field = axis.field.split(".")
            parameters[axis.field] = data[section][field]
        for adapter in suite.adapters:
            selected = [s for _, _, s in cases if s.name == scenario.name and s.adapter == adapter]
            points.append(
                PointWorkload(
                    scenario=scenario.name,
                    parameters=parameters,
                    adapter=adapter,
                    seeds=suite.seeds,
                    runs=len(selected),
                    steps=sum(s.world.steps for s in selected),
                )
            )
    return SweepWorkload(
        sweep_digest=hashlib.sha256(canonical(sweep.model_dump()).encode()).hexdigest(),
        suite_digest=suite.digest(),
        scenarios=len(suite.scenarios),
        runs=len(cases),
        steps=sum(s.world.steps for _, _, s in cases),
        points=points,
    )
