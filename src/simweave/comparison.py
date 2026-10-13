"""Pure comparison of like-for-like experiments; previews are not replay evidence."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field

from simweave.contracts import Contract, MetricName, Number, RunResult, Sample, Scenario

PREVIEW_POINTS = 101


class RegressionGate(Contract):
    metric: MetricName
    max_increase: Number = Field(ge=0)


class PreviewPoint(Contract):
    step: int = Field(ge=0, le=20_000)
    time: Number = Field(ge=0, le=2000)
    position: Number = Field(ge=-1e12, le=1e12)


class RunSummary(Contract):
    scenario: Scenario
    result: RunResult
    trajectory: list[PreviewPoint] = Field(max_length=PREVIEW_POINTS)


class MetricDelta(Contract):
    metric: MetricName
    baseline: Number
    candidate: Number
    delta: Number


class RegressionResult(Contract):
    metric: MetricName
    max_increase: Number
    increase: Number
    passed: bool


class Comparison(Contract):
    schema_version: int = Field(default=1, ge=1, le=1)
    baseline: RunSummary
    candidate: RunSummary
    metrics: list[MetricDelta]
    newly_failing_gates: list[int]
    regression_gates: list[RegressionResult]
    passed: bool
    warnings: list[str]


def preview_steps(steps: int) -> set[int]:
    count = min(steps + 1, PREVIEW_POINTS)
    return {i * steps // (count - 1) for i in range(count)}


def preview(scenario: Scenario, samples: Iterable[Sample]) -> list[PreviewPoint]:
    keep = preview_steps(scenario.world.steps)
    return [
        PreviewPoint(step=s.step, time=s.time, position=s.position)
        for s in samples
        if s.step in keep
    ]


def comparable(scenario: Scenario) -> dict:
    data = scenario.model_dump()
    del data["name"]
    data["controller"] = {"kind": scenario.controller.kind, "target": scenario.controller.target}
    return data


def validate_summary(summary: RunSummary) -> None:
    """Check summary consistency, without claiming to verify omitted telemetry."""
    s, r = summary.scenario, summary.result
    if (
        r.scenario_digest != s.digest()
        or r.adapter != s.adapter
        or r.sample_count != s.world.steps + 1
        or set(r.metrics) != {"final_error", "rmse", "max_abs_position", "control_effort"}
        or any(v < 0 for v in r.metrics.values())
        or len(r.gates) != len(s.gates)
        or r.passed != all(g.passed for g in r.gates)
        or [p.step for p in summary.trajectory] != sorted(preview_steps(s.world.steps))
        or any(p.time != p.step * s.world.timestep for p in summary.trajectory)
    ):
        raise ValueError("inconsistent run summary")
    for definition, gate in zip(s.gates, r.gates, strict=True):
        expected = (
            r.metrics[gate.metric] <= gate.threshold
            if gate.op == "lte"
            else r.metrics[gate.metric] >= gate.threshold
        )
        if (
            definition.model_dump() != gate.model_dump(include={"metric", "op", "threshold"})
            or gate.value != r.metrics[gate.metric]
            or gate.passed != expected
        ):
            raise ValueError("inconsistent quality gates")


def compare(
    baseline: RunSummary,
    candidate: RunSummary,
    gates: list[RegressionGate] | None = None,
) -> Comparison:
    validate_summary(baseline)
    validate_summary(candidate)
    if comparable(baseline.scenario) != comparable(candidate.scenario):
        raise ValueError("comparison requires matching inputs except controller tuning and name")
    metrics = [
        MetricDelta(
            metric=key,
            baseline=value,
            candidate=candidate.result.metrics[key],
            delta=candidate.result.metrics[key] - value,
        )
        for key, value in baseline.result.metrics.items()
    ]
    regression = [
        RegressionResult(
            **gate.model_dump(),
            increase=candidate.result.metrics[gate.metric] - baseline.result.metrics[gate.metric],
            passed=(
                candidate.result.metrics[gate.metric] - baseline.result.metrics[gate.metric]
                <= gate.max_increase
            ),
        )
        for gate in gates or []
    ]
    warnings = []
    if any(
        getattr(baseline.result, key) != getattr(candidate.result, key)
        for key in ("adapter_version", "engine_version", "python_version")
    ):
        warnings.append("Runtime versions differ; controller tuning may not explain the change.")
    if not baseline.result.passed:
        warnings.append(
            "Baseline quality gates failed; repair the baseline before accepting tuning."
        )
    return Comparison(
        baseline=baseline,
        candidate=candidate,
        metrics=metrics,
        newly_failing_gates=[
            i
            for i, (a, b) in enumerate(
                zip(baseline.result.gates, candidate.result.gates, strict=True)
            )
            if a.passed and not b.passed
        ],
        regression_gates=regression,
        passed=baseline.result.passed
        and candidate.result.passed
        and all(g.passed for g in regression),
        warnings=warnings,
    )
