"""Bounded paired mean-difference inference; no execution, storage, or HTTP imports."""

from __future__ import annotations

import hashlib
import math
import random
from typing import Literal

from pydantic import Field, field_validator, model_validator

from simweave.comparison import RegressionGate, comparable, compare
from simweave.contracts import Contract, MetricName, Number, canonical
from simweave.provenance import Digest, Environment
from simweave.suites import Adapter, CaseResult, SuiteReport

Role = Literal["baseline", "candidate"]
Verdict = Literal["within_tolerance", "regression", "inconclusive"]


class Versioned(Contract):
    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value


class DecisionPolicy(Versioned):
    metrics: list[RegressionGate] = Field(min_length=1, max_length=4)
    resamples: int = Field(default=5000, ge=1000, le=10000)
    random_seed: int = Field(default=1729, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def unique_metrics(self):
        if len({m.metric for m in self.metrics}) != len(self.metrics):
            raise ValueError("policy metrics must be unique")
        return self

    def digest(self) -> str:
        return hashlib.sha256(canonical(self.model_dump()).encode()).hexdigest()


class Interval(Contract):
    mean: Number
    low: Number
    high: Number
    constant: bool


def _quantile(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def paired_interval(differences: list[float], policy: DecisionPolicy) -> Interval:
    """95% percentile interval; resample whole paired differences with replacement.

    random() uses the documented seeded stream; floor(random()*n) selects an index.
    fsum and linear interpolation define algorithm paired-percentile-mean-v1.
    """
    if not 1 <= len(differences) <= 32 or not all(math.isfinite(v) for v in differences):
        raise ValueError("expected 1..32 finite paired differences")
    # Divide before summing to avoid overflow for large but finite metrics.
    n = len(differences)
    scaled = [v / n for v in differences]
    mean = math.fsum(scaled)
    constant = all(v == differences[0] for v in differences)
    if constant:
        return Interval(mean=mean, low=mean, high=mean, constant=True)
    rng = random.Random(policy.random_seed)
    means = sorted(
        math.fsum(scaled[int(rng.random() * n)] for _ in range(n)) for _ in range(policy.resamples)
    )
    return Interval(
        mean=mean,
        low=_quantile(means, 0.025),
        high=_quantile(means, 0.975),
        constant=means[0] == means[-1],
    )


class MetricDecision(Contract):
    metric: MetricName
    max_increase: Number
    interval: Interval | None
    verdict: Verdict


def interval_verdict(interval: Interval, max_increase: float, *, eligible: bool = True) -> Verdict:
    """Classify an eligible population; descriptive constant intervals cannot pass."""
    if not eligible or interval.constant:
        return "inconclusive"
    if interval.low > max_increase:
        return "regression"
    if interval.high <= max_increase:
        return "within_tolerance"
    return "inconclusive"


class GroupDecision(Contract):
    name: str
    adapter: Adapter
    seeds: list[int]
    complete_pairs: int
    quality_failures: int
    individual_regression_failures: int
    issues: list[str]
    metrics: list[MetricDecision]


class StatisticalReport(Versioned):
    algorithm: Literal["paired-percentile-mean-v1"] = "paired-percentile-mean-v1"
    confidence_level: Literal[0.95] = 0.95
    minimum_pairs: Literal[30] = 30
    policy: DecisionPolicy
    policy_digest: Digest
    baseline_suite_digest: Digest
    candidate_suite_digest: Digest
    baseline_report_digest: Digest
    candidate_report_digest: Digest
    baseline_environment: Environment | None
    candidate_environment: Environment | None
    baseline_role: Role
    candidate_role: Role
    groups: list[GroupDecision]
    status: Literal["within_tolerance", "regression", "inconclusive"]
    exit_code: Literal[0, 1, 2]
    warnings: list[str]


def _rows(report: SuiteReport, role: Role) -> dict[tuple[str, str, int], CaseResult]:
    # Revalidate even model_copy callers; a summary is evidence only after bundle validation.
    report = SuiteReport.model_validate(report.model_dump())
    return {
        (c.scenario.name, c.scenario.adapter, c.scenario.seed): c
        for c in report.cases
        if c.role == role
    }


def analyze(
    baseline: SuiteReport,
    candidate: SuiteReport,
    policy: DecisionPolicy,
    *,
    baseline_role: Role = "baseline",
    candidate_role: Role = "candidate",
    environments: tuple[Environment, Environment] | None = None,
    individual_gates: bool = False,
) -> StatisticalReport:
    """Compare explicit roles; never pair by row position or pool distinct scenarios."""
    policy = DecisionPolicy.model_validate(policy.model_dump())
    left, right = _rows(baseline, baseline_role), _rows(candidate, candidate_role)
    keys = sorted(left.keys() | right.keys())
    groups = []
    environment_changed = environments is not None and any(
        getattr(environments[0], field) != getattr(environments[1], field)
        for field in ("python", "system", "architecture", "dependencies")
    )
    for name, adapter in sorted({k[:2] for k in keys}):
        seeds = [k[2] for k in keys if k[:2] == (name, adapter)]
        issues = set()
        if environment_changed:
            issues.add("Runtime environment differs; build effects are confounded.")
        pairs = []
        failures = individual_failures = 0
        for seed in seeds:
            a, b = left.get((name, adapter, seed)), right.get((name, adapter, seed))
            if a is None or b is None or a.summary is None or b.summary is None:
                issues.add("Missing or failed run; no seeds were silently excluded.")
                continue
            if comparable(a.scenario) != comparable(b.scenario):
                issues.add("Physical inputs or quality gates differ.")
                continue
            pair = compare(
                a.summary,
                b.summary,
                candidate.suite.regression_gates if individual_gates else [],
            )
            failures += int(not a.summary.result.passed) + int(not b.summary.result.passed)
            individual_failures += sum(not g.passed for g in pair.regression_gates)
            if any(
                getattr(a.summary.result, f) != getattr(b.summary.result, f)
                for f in ("adapter_version", "engine_version", "python_version")
            ):
                issues.add("Recorded runtime versions differ; build effects are confounded.")
            pairs.append(pair)
        if len(pairs) < 30:
            issues.add("At least 30 complete paired seeds are required for a decision.")
        decisions = []
        for limit in policy.metrics:
            interval = None
            verdict = "inconclusive"
            # An incomplete/mismatched population must not produce a survivor-only estimate.
            if len(pairs) == len(seeds):
                interval = paired_interval(
                    [
                        p.candidate.result.metrics[limit.metric]
                        - p.baseline.result.metrics[limit.metric]
                        for p in pairs
                    ],
                    policy,
                )
                verdict = interval_verdict(interval, limit.max_increase, eligible=not issues)
            decisions.append(
                MetricDecision(**limit.model_dump(), interval=interval, verdict=verdict)
            )
        groups.append(
            GroupDecision(
                name=name,
                adapter=adapter,
                seeds=seeds,
                complete_pairs=len(pairs),
                quality_failures=failures,
                individual_regression_failures=individual_failures,
                issues=sorted(issues),
                metrics=decisions,
            )
        )
    failed = any(
        g.quality_failures
        or g.individual_regression_failures
        or any(m.verdict == "regression" for m in g.metrics)
        for g in groups
    )
    uncertain = any(m.verdict == "inconclusive" for g in groups for m in g.metrics)
    status = "regression" if failed else "inconclusive" if uncertain else "within_tolerance"
    return StatisticalReport(
        policy=policy,
        policy_digest=policy.digest(),
        baseline_suite_digest=baseline.suite_digest,
        candidate_suite_digest=candidate.suite_digest,
        baseline_report_digest=hashlib.sha256(
            canonical(baseline.model_dump()).encode()
        ).hexdigest(),
        candidate_report_digest=hashlib.sha256(
            canonical(candidate.model_dump()).encode()
        ).hexdigest(),
        baseline_environment=environments[0] if environments else None,
        candidate_environment=environments[1] if environments else None,
        baseline_role=baseline_role,
        candidate_role=candidate_role,
        groups=groups,
        status=status,
        exit_code={"within_tolerance": 0, "regression": 1, "inconclusive": 2}[status],
        warnings=[
            "Approximate marginal 95% intervals; no multiple-metric or repeated-build correction.",
            "Assumes independent, representative paired seeds; unique seeds do not establish this.",
            "Constant differences have a descriptive point interval, not evidence of certainty.",
            "A within-tolerance result never promotes a baseline automatically.",
        ],
    )
