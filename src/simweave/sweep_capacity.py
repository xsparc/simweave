"""Opt-in capacity report; the original workload contract stays unchanged."""

import base64
import csv
import hashlib
import io
from html import escape
from typing import Literal

from pydantic import Field, field_validator

from simweave.contracts import Contract
from simweave.suites import MAX_SUITE_RUNS, MAX_SUITE_STEPS, Adapter
from simweave.sweep_inspect import SweepWorkload, inspect_sweep
from simweave.sweeps import Sweep


class AdapterWorkload(Contract):
    adapter: Adapter
    runs: int = Field(ge=2, le=MAX_SUITE_RUNS)
    steps: int = Field(ge=1, le=MAX_SUITE_STEPS)


class SweepCapacity(Contract):
    schema_version: Literal[1] = 1
    workload: SweepWorkload
    max_runs: int = Field(default=MAX_SUITE_RUNS, ge=MAX_SUITE_RUNS, le=MAX_SUITE_RUNS)
    max_steps: int = Field(default=MAX_SUITE_STEPS, ge=MAX_SUITE_STEPS, le=MAX_SUITE_STEPS)
    remaining_runs: int = Field(ge=0, le=MAX_SUITE_RUNS - 2)
    remaining_steps: int = Field(ge=0, le=MAX_SUITE_STEPS - 2)
    adapters: list[AdapterWorkload] = Field(min_length=1, max_length=3)

    @field_validator("schema_version", "max_runs", "max_steps", mode="before")
    @classmethod
    def integer_constants(cls, value):
        if type(value) is not int:
            raise ValueError("version and limits must be integers")
        return value


def inspect_capacity(sweep: Sweep) -> SweepCapacity:
    workload = inspect_sweep(sweep)
    adapters = list(dict.fromkeys(p.adapter for p in workload.points))
    return SweepCapacity(
        workload=workload,
        remaining_runs=MAX_SUITE_RUNS - workload.runs,
        remaining_steps=MAX_SUITE_STEPS - workload.steps,
        adapters=[
            AdapterWorkload(
                adapter=adapter,
                runs=sum(p.runs for p in workload.points if p.adapter == adapter),
                steps=sum(p.steps for p in workload.points if p.adapter == adapter),
            )
            for adapter in adapters
        ],
    )


def render_capacity_csv(sweep: Sweep) -> str:
    """One row per adapter; headroom columns describe the entire admitted plan."""
    result = inspect_capacity(sweep)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(
        [
            "schema_version",
            "sweep_name_text",
            "adapter",
            "adapter_runs",
            "adapter_steps",
            "total_runs",
            "total_steps",
            "max_runs",
            "max_steps",
            "remaining_runs",
            "remaining_steps",
            "sweep_sha256",
            "suite_sha256",
            "interpretation",
        ]
    )
    for adapter in result.adapters:
        writer.writerow(
            [
                1,
                "text:" + sweep.name,
                adapter.adapter,
                adapter.runs,
                adapter.steps,
                result.workload.runs,
                result.workload.steps,
                result.max_runs,
                result.max_steps,
                result.remaining_runs,
                result.remaining_steps,
                result.workload.sweep_digest,
                result.workload.suite_digest,
                result.workload.interpretation,
            ]
        )
    return stream.getvalue()


STYLE = """
:root { font-family: system-ui, sans-serif; color: #183044; background: #f3f6f8; }
body { margin: 0; line-height: 1.6; } main { max-width: 1050px; margin: auto; padding: 2rem; }
h1 { font-size: 2.4rem; } h1, h3, p { overflow-wrap: anywhere; }
section { background: white; border: 1px solid #cdd9e0;
border-radius: .6rem; padding: 1.2rem; margin: 1rem 0; }
.cards { display: flex; flex-wrap: wrap; gap: 1rem; } .cards section { flex: 1; }
strong { font-size: 1.3rem; } .table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; } th, td { padding: .6rem;
text-align: left; border-bottom: 1px solid #dbe3e8; } code { overflow-wrap: anywhere; }
@media print { :root { background: white; } main { padding: 0; } }
"""


def render_capacity(sweep: Sweep) -> str:
    result = inspect_capacity(sweep)
    workload = result.workload
    style_hash = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    policy = (
        f"default-src 'none'; base-uri 'none'; form-action 'none'; style-src 'sha256-{style_hash}'"
    )
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{escape(policy, quote=True)}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Sweep capacity: {escape(sweep.name)}</title><style>{STYLE}</style></head>",
        f"<body><main><p>SimWeave / Planning</p><h1>{escape(sweep.name)}</h1>",
        "<p>Admitted plan. Counts include both controllers for every seed. "
        "Remaining capacity is an admission limit, not a reservation or an estimate "
        "of time, memory, storage or cost. Adapter availability is not checked.</p>",
        '<div class="cards">',
        f"<section><h2>Runs</h2><strong>{workload.runs} / {result.max_runs}</strong>"
        f"<p>{result.remaining_runs} remaining</p></section>",
        f"<section><h2>Steps</h2><strong>{workload.steps} / {result.max_steps}</strong>"
        f"<p>{result.remaining_steps} remaining</p></section></div>",
        '<section><h2>By adapter</h2><div class="table-wrap"><table>'
        '<thead><tr><th scope="col">Adapter</th><th scope="col">Runs</th>'
        '<th scope="col">Steps</th></tr></thead><tbody>',
    ]
    for adapter in result.adapters:
        parts.append(
            f'<tr><th scope="row">{escape(adapter.adapter)}</th>'
            f"<td>{adapter.runs}</td><td>{adapter.steps}</td></tr>"
        )
    parts.append("</tbody></table></div></section><section><h2>Parameter points</h2>")
    for point in workload.points:
        parameters = "; ".join(f"{key} = {value}" for key, value in point.parameters.items())
        parts.append(
            f"<h3>{escape(point.scenario)} / {escape(point.adapter)}</h3>"
            f"<p>{escape(parameters)}</p><p>Seeds: {', '.join(map(str, point.seeds))}"
            f" · Runs: {point.runs} · Steps: {point.steps}</p>"
        )
    parts.append("<h2>Evidence identity</h2>")
    for label, digest in [("Sweep", workload.sweep_digest), ("Suite", workload.suite_digest)]:
        parts.append(f"<p>{label} SHA-256<br><code>{digest}</code></p>")
    parts.append("</section></main></body></html>")
    return "".join(parts)
