"""Bounded local suite execution and portable CI reports, independent of HTTP/storage."""

from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from simweave.comparison import (
    Comparison,
    PreviewPoint,
    RegressionGate,
    RunSummary,
    compare,
    preview_steps,
    validate_summary,
)
from simweave.contracts import Contract, Controller, Number, Scenario, canonical
from simweave.engine import execute
from simweave.provenance import Environment, capture

Seed = Annotated[int, Field(ge=0, le=2**32 - 1)]
Adapter = Literal["reference", "mujoco", "gazebo"]
MAX_SUITE_RUNS = 64
MAX_SUITE_STEPS = 200_000


class Suite(Contract):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=100)
    scenarios: list[Scenario] = Field(min_length=1, max_length=8)
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
    def bounded_matrix(self):
        for name in (self.name, *(s.name for s in self.scenarios)):
            if any(
                not (
                    c in "\t\n\r"
                    or 0x20 <= ord(c) <= 0xD7FF
                    or 0xE000 <= ord(c) <= 0xFFFD
                    or 0x10000 <= ord(c) <= 0x10FFFF
                )
                for c in name
            ):
                raise ValueError("suite and scenario names must contain valid XML text")
        if len(set(self.seeds)) != len(self.seeds) or len(set(self.adapters)) != len(self.adapters):
            raise ValueError("matrix seeds and adapters must be unique")
        if len({s.name for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("scenario names must be unique")
        if len({g.metric for g in self.regression_gates}) != len(self.regression_gates):
            raise ValueError("regression metrics must be unique")
        if self.baseline.target != self.candidate.target:
            raise ValueError("controller targets must match")
        multiplier = 2 * len(self.seeds) * len(self.adapters)
        if len(self.scenarios) * multiplier > MAX_SUITE_RUNS:
            raise ValueError(f"suite exceeds {MAX_SUITE_RUNS} runs")
        if sum(s.world.steps for s in self.scenarios) * multiplier > MAX_SUITE_STEPS:
            raise ValueError(f"suite exceeds {MAX_SUITE_STEPS} total steps")
        # Revalidate all overrides now, before creating output or executing work.
        for _, _, scenario in self.expand():
            Scenario.model_validate(scenario.model_dump())
        return self

    def expand(self):
        index = 0
        for scenario in self.scenarios:
            for adapter in self.adapters:
                for seed in self.seeds:
                    for role in ("baseline", "candidate"):
                        data = scenario.model_dump()
                        data.update(
                            adapter=adapter, seed=seed, controller=getattr(self, role).model_dump()
                        )
                        yield f"case-{index:04d}", role, Scenario.model_validate(data)
                        index += 1

    def digest(self):
        return hashlib.sha256(canonical(self.model_dump()).encode()).hexdigest()


class CaseResult(Contract):
    id: str = Field(pattern=r"^case-[0-9]{4}$")
    role: Literal["baseline", "candidate"]
    scenario: Scenario
    duration_seconds: Number = Field(ge=0)
    summary: RunSummary | None
    error: Literal["adapter_unavailable", "execution_failed"] | None


class SuiteReport(Contract):
    schema_version: Literal[1] = 1
    suite: Suite
    suite_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    cases: list[CaseResult] = Field(min_length=2, max_length=MAX_SUITE_RUNS)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @model_validator(mode="after")
    def consistent(self):
        expected = list(self.suite.expand())
        if self.suite_digest != self.suite.digest() or len(self.cases) != len(expected):
            raise ValueError("suite report does not match its matrix")
        for case, (identifier, role, scenario) in zip(self.cases, expected, strict=True):
            if (case.id, case.role, case.scenario) != (identifier, role, scenario):
                raise ValueError("suite case does not match its matrix")
            if (case.summary is None) == (case.error is None):
                raise ValueError("case requires either a summary or an execution error")
            if case.summary:
                if case.summary.scenario != scenario:
                    raise ValueError("summary scenario does not match its case")
                validate_summary(case.summary)
        return self


class PairReview(Contract):
    baseline_id: str
    candidate_id: str
    name: str
    adapter: Adapter
    seed: int
    comparison: Comparison | None
    error: str | None


class SuiteReview(Contract):
    schema_version: int = Field(default=1, ge=1, le=1)
    name: str
    suite_digest: str
    exit_code: int
    pairs: list[PairReview]


def review(report: SuiteReport) -> SuiteReview:
    pairs = []
    exit_code = 0
    for baseline, candidate in zip(report.cases[::2], report.cases[1::2], strict=True):
        comparison = None
        error = None
        if baseline.summary and candidate.summary:
            comparison = compare(baseline.summary, candidate.summary, report.suite.regression_gates)
            if not comparison.passed:
                exit_code = max(exit_code, 1)
        else:
            error = "; ".join(f"{c.role}: {c.error}" for c in (baseline, candidate) if c.error)
            exit_code = 2
        pairs.append(
            PairReview(
                baseline_id=baseline.id,
                candidate_id=candidate.id,
                name=baseline.scenario.name,
                adapter=baseline.scenario.adapter,
                seed=baseline.scenario.seed,
                comparison=comparison,
                error=error,
            )
        )
    return SuiteReview(
        name=report.suite.name, suite_digest=report.suite_digest, exit_code=exit_code, pairs=pairs
    )


def write_junit(report: SuiteReport, path: Path) -> None:
    root = ET.Element("testsuite", name=report.suite.name)
    failures = errors = 0
    for case in report.cases:
        node = ET.SubElement(
            root,
            "testcase",
            name=f"{case.id}.{case.role}",
            classname=f"{case.scenario.name}.{case.scenario.adapter}.seed-{case.scenario.seed}",
            time=f"{case.duration_seconds:.6f}",
        )
        if case.error:
            ET.SubElement(node, "error", message=case.error, type=case.error)
            errors += 1
        elif not case.summary.result.passed:
            failed = [g.metric for g in case.summary.result.gates if not g.passed]
            ET.SubElement(node, "failure", message="Quality gates failed: " + ", ".join(failed))
            failures += 1
        ET.SubElement(node, "system-out").text = f"Recording: {case.id}/"
    for pair in review(report).pairs:
        if not pair.comparison or not pair.comparison.regression_gates:
            continue
        node = ET.SubElement(
            root,
            "testcase",
            name=f"{pair.candidate_id}.regression",
            classname=f"{pair.name}.{pair.adapter}.seed-{pair.seed}",
        )
        failed = [g.metric for g in pair.comparison.regression_gates if not g.passed]
        if failed:
            ET.SubElement(node, "failure", message="Metric increase exceeded: " + ", ".join(failed))
            failures += 1
    root.set("tests", str(len(root)))
    root.set("failures", str(failures))
    root.set("errors", str(errors))
    root.set("time", str(sum(c.duration_seconds for c in report.cases)))
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


class RecordingWriteError(OSError):
    """Abort the suite when recording storage fails, even inside the execution sink."""


def execute_suite(
    suite: Suite, output: Path, *, environment: Environment | None = None, checkpoint=None
) -> SuiteReport:
    environment = environment or capture()
    output.mkdir(parents=True, exist_ok=False)
    (output / "suite.json").write_text(suite.model_dump_json(indent=2), encoding="utf-8")
    cases = []
    for identifier, role, scenario in suite.expand():
        if checkpoint:
            checkpoint()
        directory = output / identifier
        directory.mkdir()
        (directory / "scenario.json").write_text(scenario.model_dump_json(), encoding="utf-8")
        keep, trajectory = preview_steps(scenario.world.steps), []
        started = time.monotonic()
        error = summary = None
        with (directory / "telemetry.jsonl").open("w", encoding="utf-8", newline="\n") as stream:

            def sink(sample, stream=stream, keep=keep, trajectory=trajectory):
                if checkpoint:
                    checkpoint()
                try:
                    stream.write(canonical(sample.model_dump()) + "\n")
                except OSError as exc:
                    raise RecordingWriteError("recording storage failed") from exc
                if sample.step in keep:
                    trajectory.append(
                        PreviewPoint(step=sample.step, time=sample.time, position=sample.position)
                    )

            try:
                result = execute(scenario, sink)
            except (RecordingWriteError, SuiteInterrupted):
                raise  # Storage failures must not masquerade as simulator failures.
            except Exception as exc:
                error = (
                    "adapter_unavailable" if isinstance(exc, ImportError) else "execution_failed"
                )
            else:
                summary = RunSummary(scenario=scenario, result=result, trajectory=trajectory)
        if summary:
            (directory / "result.json").write_text(
                summary.result.model_dump_json(), encoding="utf-8"
            )
        cases.append(
            CaseResult(
                id=identifier,
                role=role,
                scenario=scenario,
                duration_seconds=time.monotonic() - started,
                summary=summary,
                error=error,
            )
        )
    report = SuiteReport(suite=suite, suite_digest=suite.digest(), cases=cases)
    (output / "report.json").write_text(report.model_dump_json(), encoding="utf-8")
    (output / "summary.json").write_text(review(report).model_dump_json(), encoding="utf-8")
    write_junit(report, output / "junit.xml")
    from simweave.bundles import write_bundle
    from simweave.offline import write_report

    (output / "environment.json").write_text(environment.model_dump_json(), encoding="utf-8")
    write_report(report, output / "report.html", environment)
    write_bundle(report, environment, output)
    return report


class SuiteInterrupted(Exception):
    """An execution owner withdrew permission to continue this suite."""
