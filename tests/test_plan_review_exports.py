import csv
import io
import json
import subprocess
import sys

import pytest
from test_sweep_diff import source

from simweave.cli import main
from simweave.sweep_diff import (
    PlanDifference,
    PlanDifferenceV2,
    compare_plans,
    render_plan_diff_csv,
    verify_plan_diff,
)


def test_adapter_union_counts_and_version_compatibility():
    before = source(adapters=["gazebo", "reference"])
    after = source(adapters=["reference", "mujoco"], seeds=[1, 2])
    legacy = compare_plans(before, after)
    assert type(legacy) is PlanDifference and "adapter_deltas" not in legacy.model_dump()
    result = compare_plans(before, after, schema_version=2)
    assert [a.adapter for a in result.adapter_deltas] == ["gazebo", "reference", "mujoco"]
    assert [(a.before_runs, a.after_runs) for a in result.adapter_deltas] == [
        (4, 0),
        (4, 8),
        (0, 8),
    ]
    assert sum(a.runs_delta for a in result.adapter_deltas) == result.runs_delta
    assert sum(a.steps_delta for a in result.adapter_deltas) == result.steps_delta
    reverse = compare_plans(after, before, schema_version=2)
    for a in result.adapter_deltas:
        inverse = next(b for b in reverse.adapter_deltas if b.adapter == a.adapter)
        assert inverse.runs_delta == -a.runs_delta and inverse.steps_delta == -a.steps_delta


@pytest.mark.parametrize("mutation", ["sum", "order", "presence", "delta", "version"])
def test_v2_rejects_inconsistent_counts(mutation):
    data = compare_plans(source(), source(adapters=["mujoco"]), schema_version=2).model_dump()
    if mutation == "sum":
        data["adapter_deltas"][0]["before_runs"] += 2
        data["adapter_deltas"][0]["runs_delta"] -= 2
    elif mutation == "order":
        data["adapter_deltas"].reverse()
    elif mutation == "presence":
        data["adapter_deltas"][0]["before_steps"] = 0
        data["adapter_deltas"][0]["steps_delta"] = 0
    elif mutation == "delta":
        data["adapter_deltas"][0]["runs_delta"] = 0
    else:
        data["schema_version"] = 2.0
    with pytest.raises(ValueError):
        PlanDifferenceV2.model_validate(data)


def test_csv_safe_labels_global_totals_and_exact_bytes(tmp_path, capsys):
    before = source(name='=HYPERLINK("x")\r\n雪,', adapters=["gazebo", "reference"])
    after = source(name="+formula", adapters=["mujoco"])
    output = render_plan_diff_csv(before, after)
    rows = list(csv.DictReader(io.StringIO(output, newline="")))
    assert len(rows) == 4 and rows[0]["scope"] == "global"
    assert all(r["before_name_text"] == "text:" + before.name for r in rows)
    assert all(r["after_name_text"] == "text:+formula" for r in rows)
    assert all(r["direction"] == "after_minus_before" for r in rows)
    for field in (
        "before_runs",
        "after_runs",
        "runs_delta",
        "before_steps",
        "after_steps",
        "steps_delta",
    ):
        assert sum(int(r[field]) for r in rows[1:]) == int(rows[0][field])
    paths = [tmp_path / "before.json", tmp_path / "after.json"]
    for path, value in zip(paths, [before, after], strict=True):
        path.write_text(value.model_dump_json(), encoding="utf-8")
    args = ["sweep-diff", *map(str, paths), "--format", "csv"]
    target = tmp_path / "report.csv"
    assert main([*args, "--output", str(target)]) == 0
    assert target.read_bytes() == output.encode("utf-8")
    assert main([*args, "--output", str(target)]) == 2
    result = subprocess.run(
        [sys.executable, "-m", "simweave.cli", *args], capture_output=True, check=True
    )
    assert result.stdout == target.read_bytes()


@pytest.mark.parametrize("version", [1, 2])
def test_source_bound_verification_rejects_tampering_and_reversal(version):
    before, after = source(), source(name="after", seeds=[2])
    raw = compare_plans(before, after, schema_version=version).model_dump_json().encode()
    assert verify_plan_diff(before, after, raw).schema_version == version
    with pytest.raises(ValueError):
        verify_plan_diff(after, before, raw)
    for field, value in [
        ("name", "altered"),
        ("sweep_digest", "a" * 64),
        ("suite_digest", "b" * 64),
    ]:
        data = json.loads(raw)
        data["before"][field] = value
        with pytest.raises(ValueError):
            verify_plan_diff(before, after, json.dumps(data).encode())
    with pytest.raises(ValueError):
        verify_plan_diff(before, after, raw + b" " * 65536)
    # Keep the tampered report internally consistent: source checking must still reject it.
    data = json.loads(raw)
    data["before"]["runs"] += 2
    data["before"]["remaining_runs"] -= 2
    data["runs_delta"] -= 2
    data["remaining_runs_delta"] += 2
    if version == 2:
        data["adapter_deltas"][0]["before_runs"] += 2
        data["adapter_deltas"][0]["runs_delta"] -= 2
    model = PlanDifference if version == 1 else PlanDifferenceV2
    model.model_validate(data)
    with pytest.raises(ValueError):
        verify_plan_diff(before, after, json.dumps(data).encode())


def test_cli_verification_is_bounded_and_read_only(tmp_path, capsys):
    before, after = source(), source(seeds=[2])
    paths = [tmp_path / name for name in ("before.json", "after.json", "report.json")]
    values = [before, after, compare_plans(before, after, schema_version=2)]
    for path, value in zip(paths, values, strict=True):
        path.write_text(value.model_dump_json(), encoding="utf-8")
    original = [path.read_bytes() for path in paths]
    assert main(["sweep-diff-verify", *map(str, paths)]) == 0
    assert json.loads(capsys.readouterr().out)["verified"] is True
    assert [path.read_bytes() for path in paths] == original
    paths[2].write_bytes(b" " * 65537)
    assert main(["sweep-diff-verify", *map(str, paths)]) == 2
    assert not capsys.readouterr().out
    for index in (0, 1):
        paths[2].write_bytes(original[2])
        paths[index].write_bytes(b" " * 65537)
        assert main(["sweep-diff-verify", *map(str, paths)]) == 2
        paths[index].write_bytes(original[index])


def test_v2_schema_is_explicit(capsys):
    assert main(["sweep-diff-schema", "--schema-version", "2"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["schema_version"]["const"] == 2
    assert "adapter_deltas" in schema["required"]
