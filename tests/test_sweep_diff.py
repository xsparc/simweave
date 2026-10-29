"""Directional planning evidence, strict admission and script-free rendering."""

import base64
import hashlib
import json
from html.parser import HTMLParser

import pytest

from simweave.cli import main
from simweave.sweep_diff import STYLE, PlanDifference, compare_plans, render_plan_diff
from simweave.sweeps import Sweep


def source(**updates):
    data = {
        "name": "before",
        "scenario": {"world": {"steps": 10}},
        "axes": [{"field": "robot.mass", "values": [1.0, 2.0]}],
        "seeds": [1],
        "adapters": ["reference"],
        "baseline": {},
        "candidate": {},
    }
    data.update(updates)
    return Sweep.model_validate(data)


def test_direction_counts_identities_and_adapter_changes():
    before = source(adapters=["gazebo", "reference"])
    after = source(name="after", seeds=[1, 2, 3], adapters=["mujoco"])
    result = compare_plans(before, after)
    assert (result.before.runs, result.after.runs, result.runs_delta) == (8, 12, 4)
    assert result.steps_delta == 40
    assert result.remaining_runs_delta == -4 and result.remaining_steps_delta == -40
    assert result.added_adapters == ["mujoco"]
    assert result.removed_adapters == ["gazebo", "reference"]
    inverse = compare_plans(after, before)
    assert inverse.runs_delta == -result.runs_delta
    assert inverse.steps_delta == -result.steps_delta
    assert inverse.before == result.after and inverse.after == result.before
    assert compare_plans(before, after).model_dump_json() == result.model_dump_json()


def test_unchanged_counts_do_not_claim_equal_inputs_or_results(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("planning must not execute simulation")

    monkeypatch.setattr("simweave.suites.execute", forbidden)
    same = compare_plans(source(), source())
    assert same.identical_inputs and same.runs_delta == same.steps_delta == 0
    changed = compare_plans(source(), source(seeds=[2]))
    assert not changed.identical_inputs and changed.runs_delta == changed.steps_delta == 0
    assert changed.before.suite_digest != changed.after.suite_digest
    assert changed.interpretation == "planned_changes_not_result_equivalence"


@pytest.mark.parametrize("side", ["before", "after"])
def test_both_inputs_revalidated_before_report(side):
    bad = source()
    bad.seeds.extend(range(2, 33))
    args = (bad, source()) if side == "before" else (source(), bad)
    with pytest.raises(ValueError):
        compare_plans(*args)
    with pytest.raises(ValueError):
        render_plan_diff(*args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("runs_delta", 7),
        ("identical_inputs", False),
        ("added_adapters", ["gazebo"]),
    ],
)
def test_contract_rejects_inconsistent_or_noninteger_evidence(field, value):
    data = compare_plans(source(), source()).model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        PlanDifference.model_validate(data)


class StaticHTML(HTMLParser):
    def handle_starttag(self, tag, attrs):
        assert tag not in {"script", "iframe", "img", "link", "form"}
        assert not any(k.startswith("on") for k, _ in attrs)


def test_html_encodes_titles_and_preserves_evidence_and_csp():
    before = source(name='</h3><script>alert("x")</script>')
    after = source(name="after", seeds=[1, 2])
    output = render_plan_diff(before, after)
    StaticHTML().feed(output)
    assert "&lt;script&gt;" in output and "<script>" not in output
    result = compare_plans(before, after)
    for snapshot in [result.before, result.after]:
        assert snapshot.sweep_digest in output and snapshot.suite_digest in output
    digest = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    assert f"sha256-{digest}" in output
    assert "<td>+4</td>" in output and "<td>-4</td>" in output


@pytest.mark.parametrize("format", ["json", "html"])
def test_cli_direction_exclusive_output_and_bounded_inputs(tmp_path, capsys, format):
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    before.write_text(source().model_dump_json(), encoding="utf-8")
    after.write_text(source(seeds=[1, 2]).model_dump_json(), encoding="utf-8")
    args = ["sweep-diff", str(before), str(after), "--format", format]
    assert main(args) == 0
    stdout = capsys.readouterr().out
    if format == "json":
        assert json.loads(stdout)["runs_delta"] == 4
    else:
        assert "<td>+4</td>" in stdout
    target = tmp_path / "report"
    assert main(args + ["--output", str(target)]) == 0
    original = target.read_bytes()
    assert main(args + ["--output", str(target)]) == 2
    assert target.read_bytes() == original
    capsys.readouterr()
    for path in (before, after):
        saved = path.read_bytes()
        path.write_bytes(b" " * 65537)
        rejected = tmp_path / "rejected"
        assert main(args + ["--output", str(rejected)]) == 2
        assert not rejected.exists() and not capsys.readouterr().out
        path.write_bytes(saved)


def test_cli_schema(capsys):
    assert main(["sweep-diff-schema"]) == 0
    assert json.loads(capsys.readouterr().out) == PlanDifference.model_json_schema()
