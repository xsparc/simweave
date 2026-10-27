"""Capacity arithmetic, backward compatibility and static HTML boundaries."""

import json
from html.parser import HTMLParser

import pytest

from simweave.cli import main
from simweave.sweep_capacity import SweepCapacity, inspect_capacity, render_capacity
from simweave.sweep_inspect import inspect_sweep
from simweave.sweeps import Sweep


def source():
    return Sweep.model_validate(
        {
            "name": '</title><script>alert("x")</script>',
            "scenario": {"world": {"steps": 10}},
            "axes": [{"field": "robot.mass", "values": [1.0, 2.0]}],
            "seeds": [8, 3],
            "adapters": ["gazebo", "reference"],
            "baseline": {},
            "candidate": {},
        }
    )


def test_capacity_and_adapter_totals_preserve_workload():
    sweep = source()
    result = inspect_capacity(sweep)
    assert result.workload == inspect_sweep(sweep)
    assert result.remaining_runs == 48 and result.remaining_steps == 199840
    assert [(a.adapter, a.runs, a.steps) for a in result.adapters] == [
        ("gazebo", 8, 80),
        ("reference", 8, 80),
    ]
    assert sum(a.runs for a in result.adapters) == result.workload.runs
    assert sum(a.steps for a in result.adapters) == result.workload.steps


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("max_runs", 64.0),
        ("max_steps", 200000.0),
    ],
)
def test_capacity_constants_are_strict(field, value):
    data = inspect_capacity(source()).model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        SweepCapacity.model_validate(data)


@pytest.mark.parametrize("boundary", ["runs", "steps"])
def test_zero_headroom_at_admission_boundary(boundary):
    data = source().model_dump()
    if boundary == "runs":
        data["seeds"] = list(range(8))
    else:
        data["scenario"]["world"]["steps"] = 12500
    result = inspect_capacity(Sweep.model_validate(data))
    assert getattr(result, "remaining_" + boundary) == 0


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        assert not any(name.startswith("on") for name, _ in attrs)


def test_html_escapes_source_and_contains_only_static_content():
    output = render_capacity(source())
    tags = Tags()
    tags.feed(output)
    assert not set(tags.tags) & {"script", "iframe", "img", "link", "form"}
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in output
    assert "48 remaining" in output and "199840 remaining" in output
    assert inspect_sweep(source()).suite_digest in output
    assert "Content-Security-Policy" in output


@pytest.mark.parametrize("format", ["capacity-json", "html"])
def test_cli_exclusive_output_and_invalid_input(tmp_path, capsys, format):
    path = tmp_path / "sweep.json"
    path.write_text(source().model_dump_json(), encoding="utf-8")
    assert main(["sweep-inspect", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == inspect_sweep(source()).model_dump()
    args = ["sweep-inspect", str(path), "--format", format]
    assert main(args) == 0
    output = capsys.readouterr().out
    assert "remaining_runs" in output if format == "capacity-json" else "<!doctype html>" in output
    target = tmp_path / "report"
    assert main(args + ["--output", str(target)]) == 0
    original = target.read_bytes()
    assert main(args + ["--output", str(target)]) == 2
    assert target.read_bytes() == original
    data = source().model_dump()
    data["seeds"] = list(range(32))
    path.write_text(json.dumps(data), encoding="utf-8")
    rejected = tmp_path / "rejected"
    assert main(args + ["--output", str(rejected)]) == 2
    assert not rejected.exists()
