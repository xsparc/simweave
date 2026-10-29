"""Directional, plan-only comparison of two independently admitted sweeps."""

import base64
import hashlib
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


def compare_plans(before: Sweep, after: Sweep) -> PlanDifference:
    """Revalidate both sources and generated suites before producing any report."""
    old, new = _snapshot(before), _snapshot(after)
    return PlanDifference(
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
