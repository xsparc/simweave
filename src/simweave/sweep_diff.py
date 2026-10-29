"""Directional, plan-only comparison of two independently admitted sweeps."""

import base64
import csv
import hashlib
import io
import json
from html import escape
from typing import Literal

from pydantic import Field, field_validator, model_validator

from simweave.contracts import Contract
from simweave.suites import MAX_SUITE_RUNS, MAX_SUITE_STEPS, Adapter
from simweave.sweep_capacity import STYLE as CAPACITY_STYLE
from simweave.sweep_capacity import inspect_capacity
from simweave.sweeps import Sweep

STYLE = (
    CAPACITY_STYLE
    + """
@media (max-width: 600px) {
  main { padding: 1rem; }
  th, td { padding: .3rem; font-size: .85rem; }
}
"""
)


class PlanSnapshot(Contract):
    name: str = Field(min_length=1, max_length=100)
    sweep_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    suite_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    runs: int = Field(ge=2, le=MAX_SUITE_RUNS)
    steps: int = Field(ge=2, le=MAX_SUITE_STEPS)
    remaining_runs: int = Field(ge=0, le=MAX_SUITE_RUNS - 2)
    remaining_steps: int = Field(ge=0, le=MAX_SUITE_STEPS - 2)
    adapters: list[Adapter] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def consistent(self):
        if (
            self.runs + self.remaining_runs != MAX_SUITE_RUNS
            or self.steps + self.remaining_steps != MAX_SUITE_STEPS
        ):
            raise ValueError("inconsistent capacity")
        if len(set(self.adapters)) != len(self.adapters):
            raise ValueError("duplicate adapters")
        return self


class PlanDifference(Contract):
    schema_version: Literal[1] = 1
    before: PlanSnapshot
    after: PlanSnapshot
    runs_delta: int = Field(ge=-MAX_SUITE_RUNS, le=MAX_SUITE_RUNS)
    steps_delta: int = Field(ge=-MAX_SUITE_STEPS, le=MAX_SUITE_STEPS)
    remaining_runs_delta: int = Field(ge=-MAX_SUITE_RUNS, le=MAX_SUITE_RUNS)
    remaining_steps_delta: int = Field(ge=-MAX_SUITE_STEPS, le=MAX_SUITE_STEPS)
    added_adapters: list[Adapter] = Field(max_length=3)
    removed_adapters: list[Adapter] = Field(max_length=3)
    identical_inputs: bool
    interpretation: Literal["planned_changes_not_result_equivalence"] = (
        "planned_changes_not_result_equivalence"
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @model_validator(mode="after")
    def consistent(self):
        for field in ("runs", "steps", "remaining_runs", "remaining_steps"):
            if getattr(self, field + "_delta") != getattr(self.after, field) - getattr(
                self.before, field
            ):
                raise ValueError("inconsistent directional delta")
        if self.added_adapters != [
            a for a in self.after.adapters if a not in self.before.adapters
        ] or self.removed_adapters != [
            a for a in self.before.adapters if a not in self.after.adapters
        ]:
            raise ValueError("inconsistent adapter changes")
        if self.identical_inputs != (self.before.sweep_digest == self.after.sweep_digest):
            raise ValueError("inconsistent input identity")
        return self


class AdapterDifference(Contract):
    adapter: Adapter
    before_runs: int = Field(ge=0, le=MAX_SUITE_RUNS)
    after_runs: int = Field(ge=0, le=MAX_SUITE_RUNS)
    runs_delta: int = Field(ge=-MAX_SUITE_RUNS, le=MAX_SUITE_RUNS)
    before_steps: int = Field(ge=0, le=MAX_SUITE_STEPS)
    after_steps: int = Field(ge=0, le=MAX_SUITE_STEPS)
    steps_delta: int = Field(ge=-MAX_SUITE_STEPS, le=MAX_SUITE_STEPS)

    @model_validator(mode="after")
    def consistent(self):
        for field in ("runs", "steps"):
            if getattr(self, field + "_delta") != getattr(self, "after_" + field) - getattr(
                self, "before_" + field
            ):
                raise ValueError("inconsistent adapter delta")
        for side in ("before", "after"):
            runs, steps = getattr(self, side + "_runs"), getattr(self, side + "_steps")
            if (runs == 0) != (steps == 0) or steps < runs:
                raise ValueError("inconsistent adapter counts")
        return self


class PlanDifferenceV2(PlanDifference):
    schema_version: Literal[2] = 2
    adapter_deltas: list[AdapterDifference] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def consistent_adapters(self):
        expected = list(dict.fromkeys(self.before.adapters + self.after.adapters))
        if [item.adapter for item in self.adapter_deltas] != expected:
            raise ValueError("inconsistent adapter union order")
        for side in ("before", "after"):
            snapshot = getattr(self, side)
            for field in ("runs", "steps"):
                if sum(getattr(a, side + "_" + field) for a in self.adapter_deltas) != getattr(
                    snapshot, field
                ):
                    raise ValueError("adapter counts do not sum to plan totals")
            for item in self.adapter_deltas:
                if (getattr(item, side + "_runs") > 0) != (item.adapter in snapshot.adapters):
                    raise ValueError("adapter presence differs from counts")
        return self


def _snapshot(source: Sweep) -> PlanSnapshot:
    result = inspect_capacity(source)
    return PlanSnapshot(
        name=source.name,
        sweep_digest=result.workload.sweep_digest,
        suite_digest=result.workload.suite_digest,
        runs=result.workload.runs,
        steps=result.workload.steps,
        remaining_runs=result.remaining_runs,
        remaining_steps=result.remaining_steps,
        adapters=[a.adapter for a in result.adapters],
    )


def compare_plans(before: Sweep, after: Sweep, *, schema_version: int = 1) -> PlanDifference:
    """Revalidate both sources and generated suites before producing any report."""
    if type(schema_version) is not int or schema_version not in (1, 2):
        raise ValueError("unsupported comparison version")
    old, new = _snapshot(before), _snapshot(after)
    result = PlanDifference(
        before=old,
        after=new,
        runs_delta=new.runs - old.runs,
        steps_delta=new.steps - old.steps,
        remaining_runs_delta=new.remaining_runs - old.remaining_runs,
        remaining_steps_delta=new.remaining_steps - old.remaining_steps,
        added_adapters=[a for a in new.adapters if a not in old.adapters],
        removed_adapters=[a for a in old.adapters if a not in new.adapters],
        identical_inputs=old.sweep_digest == new.sweep_digest,
    )
    if schema_version == 1:
        return result
    old_counts = {a.adapter: a for a in inspect_capacity(before).adapters}
    new_counts = {a.adapter: a for a in inspect_capacity(after).adapters}
    deltas = []
    for adapter in dict.fromkeys(old.adapters + new.adapters):
        values = {}
        for field in ("runs", "steps"):
            values["before_" + field] = getattr(old_counts.get(adapter), field, 0)
            values["after_" + field] = getattr(new_counts.get(adapter), field, 0)
            values[field + "_delta"] = values["after_" + field] - values["before_" + field]
        deltas.append(AdapterDifference(adapter=adapter, **values))
    return PlanDifferenceV2.model_validate(
        result.model_dump() | {"schema_version": 2, "adapter_deltas": deltas}
    )


def verify_plan_diff(before: Sweep, after: Sweep, raw: bytes) -> PlanDifference:
    """Check retained source consistency; not a signature or execution attestation."""
    if len(raw) > 65_536:
        raise ValueError("plan comparison exceeds 64 KiB")
    data = json.loads(raw)
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        raise ValueError("invalid comparison version")
    model = {1: PlanDifference, 2: PlanDifferenceV2}.get(data["schema_version"])
    if model is None:
        raise ValueError("unsupported comparison version")
    report = model.model_validate(data)
    expected = compare_plans(before, after, schema_version=report.schema_version)
    if report != expected:
        raise ValueError("comparison differs from retained sources")
    return report


def render_plan_diff_csv(before: Sweep, after: Sweep) -> str:
    result = compare_plans(before, after, schema_version=2)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(
        [
            "schema_version",
            "direction",
            "scope",
            "adapter",
            "before_name_text",
            "after_name_text",
            "before_runs",
            "after_runs",
            "runs_delta",
            "before_steps",
            "after_steps",
            "steps_delta",
            "before_sweep_sha256",
            "after_sweep_sha256",
            "before_suite_sha256",
            "after_suite_sha256",
            "interpretation",
        ]
    )
    rows = [
        (
            "global",
            "",
            result.before.runs,
            result.after.runs,
            result.runs_delta,
            result.before.steps,
            result.after.steps,
            result.steps_delta,
        )
    ]
    rows.extend(
        (
            "adapter",
            a.adapter,
            a.before_runs,
            a.after_runs,
            a.runs_delta,
            a.before_steps,
            a.after_steps,
            a.steps_delta,
        )
        for a in result.adapter_deltas
    )
    for scope, adapter, *counts in rows:
        writer.writerow(
            [
                2,
                "after_minus_before",
                scope,
                adapter,
                "text:" + result.before.name,
                "text:" + result.after.name,
                *counts,
                result.before.sweep_digest,
                result.after.sweep_digest,
                result.before.suite_digest,
                result.after.suite_digest,
                result.interpretation,
            ]
        )
    return stream.getvalue()


def render_plan_diff(before: Sweep, after: Sweep) -> str:
    result = compare_plans(before, after)
    style_hash = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    policy = (
        f"default-src 'none'; base-uri 'none'; form-action 'none'; style-src 'sha256-{style_hash}'"
    )
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{escape(policy, quote=True)}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Sweep plan comparison</title><style>{STYLE}</style></head><body><main>",
        "<p>SimWeave / Planning</p><h1>Sweep plan comparison</h1>",
        "<p>Changes are after minus before. Counts describe admitted plans, not execution results, "
        "adapter availability, resource reservations or time estimates. Equal counts do not imply "
        "equivalent experiments or physics.</p>",
        f"<p>Identical normalized inputs: {'yes' if result.identical_inputs else 'no'}</p>",
        '<section><h2>Capacity changes</h2><div class="table-wrap"><table><thead><tr>'
        '<th scope="col">Count</th><th scope="col">Before</th><th scope="col">After</th>'
        '<th scope="col">Change</th></tr></thead><tbody>',
    ]
    for field, label in [
        ("runs", "Runs"),
        ("steps", "Steps"),
        ("remaining_runs", "Remaining runs"),
        ("remaining_steps", "Remaining steps"),
    ]:
        parts.append(
            f'<tr><th scope="row">{label}</th><td>{getattr(result.before, field)}</td>'
            f"<td>{getattr(result.after, field)}</td>"
            f"<td>{getattr(result, field + '_delta'):+d}</td></tr>"
        )
    parts.append("</tbody></table></div><h2>Adapter changes</h2>")
    for label, values in [("Added", result.added_adapters), ("Removed", result.removed_adapters)]:
        parts.append(f"<p>{label}: {escape(', '.join(values)) if values else 'none'}</p>")
    parts.append("</section>")
    for label, snapshot in [("Before", result.before), ("After", result.after)]:
        parts.append(
            f"<section><h2>{label}</h2><h3>{escape(snapshot.name)}</h3>"
            f"<p>Adapters: {escape(', '.join(snapshot.adapters))}</p>"
            f"<p>Sweep SHA-256<br><code>{snapshot.sweep_digest}</code></p>"
            f"<p>Suite SHA-256<br><code>{snapshot.suite_digest}</code></p></section>"
        )
    parts.append("</main></body></html>")
    return "".join(parts)
