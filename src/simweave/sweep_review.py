"""Descriptive results for explicit parameter grids; no inference or selection."""

import hashlib
from statistics import mean
from typing import Literal

from pydantic import Field, field_validator

from simweave.contracts import Contract, MetricName, Number, canonical
from simweave.suites import Adapter, Seed, SuiteReport, review
from simweave.sweeps import Sweep, plan


class MetricSummary(Contract):
    metric: MetricName
    baseline_mean: Number
    candidate_mean: Number
    delta_mean: Number
    delta_min: Number
    delta_max: Number


class PointReview(Contract):
    scenario: str
    parameters: dict[str, Number]
    adapter: Adapter
    seeds: list[Seed]
    passed_pairs: int = Field(ge=0, le=32)
    failed_pairs: int = Field(ge=0, le=32)
    error_pairs: int = Field(ge=0, le=32)
    metrics: list[MetricSummary] | None
    warnings: list[str]


class SweepReview(Contract):
    schema_version: Literal[1] = 1
    suite_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    sweep_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    report_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    exit_code: Literal[0, 1, 2]
    points: list[PointReview] = Field(min_length=1, max_length=24)
    interpretation: Literal["descriptive_only"] = "descriptive_only"

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value


def summarize(sweep: Sweep, report: SuiteReport) -> SweepReview:
    """Reject mismatched/mutated inputs; never silently average surviving seeds."""
    sweep = Sweep.model_validate(sweep.model_dump())
    report = SuiteReport.model_validate(report.model_dump())
    expected = plan(sweep)
    if expected != report.suite or expected.digest() != report.suite_digest:
        raise ValueError("report does not match the planned sweep")
    reviewed = review(report)
    points = []
    for scenario in expected.scenarios:
        data = scenario.model_dump()
        parameters = {}
        for axis in sweep.axes:
            section, field = axis.field.split(".")
            parameters[axis.field] = data[section][field]
        for adapter in expected.adapters:
            pairs = [p for p in reviewed.pairs if p.name == scenario.name and p.adapter == adapter]
            comparisons = [p.comparison for p in pairs if p.comparison is not None]
            errors = len(pairs) - len(comparisons)
            metrics = None
            if not errors:
                metrics = []
                for metric in ("final_error", "rmse", "max_abs_position", "control_effort"):
                    values = [next(m for m in c.metrics if m.metric == metric) for c in comparisons]
                    metrics.append(
                        MetricSummary(
                            metric=metric,
                            baseline_mean=mean(m.baseline for m in values),
                            candidate_mean=mean(m.candidate for m in values),
                            delta_mean=mean(m.delta for m in values),
                            delta_min=min(m.delta for m in values),
                            delta_max=max(m.delta for m in values),
                        )
                    )
            warnings = sorted({w for c in comparisons for w in c.warnings})
            if errors:
                warnings.append("Execution errors: metric summaries withheld for this point.")
            points.append(
                PointReview(
                    scenario=scenario.name,
                    parameters=parameters,
                    adapter=adapter,
                    seeds=[p.seed for p in pairs],
                    passed_pairs=sum(c.passed for c in comparisons),
                    failed_pairs=sum(not c.passed for c in comparisons),
                    error_pairs=errors,
                    metrics=metrics,
                    warnings=warnings,
                )
            )
    return SweepReview(
        suite_digest=expected.digest(),
        sweep_digest=hashlib.sha256(canonical(sweep.model_dump()).encode()).hexdigest(),
        report_digest=hashlib.sha256(canonical(report.model_dump()).encode()).hexdigest(),
        exit_code=reviewed.exit_code,
        points=points,
    )
