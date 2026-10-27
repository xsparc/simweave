"""Capacity integration contracts, CSV quoting and admission consistency."""

import csv
import io
import json
import subprocess
import sys

import pytest

from simweave.cli import main
from simweave.suites import MAX_SUITE_RUNS, MAX_SUITE_STEPS
from simweave.sweep_capacity import SweepCapacity, inspect_capacity, render_capacity_csv
from simweave.sweeps import Sweep


def source():
    return Sweep.model_validate(
        {
            "name": '=1+1,"\n@formula',
            "scenario": {"world": {"steps": 10}},
            "axes": [{"field": "robot.mass", "values": [1.0, 2.0]}],
            "seeds": [8, 3],
            "adapters": ["gazebo", "reference"],
            "baseline": {},
            "candidate": {},
        }
    )


def test_capacity_schema_matches_contract(capsys):
    assert main(["sweep-capacity-schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema == SweepCapacity.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["max_runs"]["minimum"] == MAX_SUITE_RUNS
    assert schema["properties"]["max_steps"]["maximum"] == MAX_SUITE_STEPS
    assert schema["$defs"]["SweepWorkload"]["properties"]["runs"]["maximum"] == MAX_SUITE_RUNS
    assert schema["$defs"]["AdapterWorkload"]["properties"]["steps"]["maximum"] == MAX_SUITE_STEPS


def test_csv_roundtrip_preserves_totals_identity_order_and_hostile_text():
    sweep = source()
    output = render_capacity_csv(sweep)
    assert output == render_capacity_csv(sweep)
    rows = list(csv.DictReader(io.StringIO(output, newline="")))
    assert [r["adapter"] for r in rows] == ["gazebo", "reference"]
    result = inspect_capacity(sweep)
    for row in rows:
        assert row["sweep_name_text"] == "text:" + sweep.name
        assert row["suite_sha256"] == result.workload.suite_digest
        assert row["sweep_sha256"] == result.workload.sweep_digest
        assert row["interpretation"] == "planned_counts_not_runtime_estimates"
        assert int(row["remaining_runs"]) + int(row["total_runs"]) == MAX_SUITE_RUNS
        assert int(row["remaining_steps"]) + int(row["total_steps"]) == MAX_SUITE_STEPS
    assert sum(int(r["adapter_runs"]) for r in rows) == 16
    assert sum(int(r["adapter_steps"]) for r in rows) == 160


def test_csv_cli_bytes_exclusive_output_and_invalid_input(tmp_path):
    path = tmp_path / "sweep.json"
    path.write_text(source().model_dump_json(), encoding="utf-8")
    args = [sys.executable, "-m", "simweave.cli", "sweep-inspect", str(path), "--format", "csv"]
    output = subprocess.run(args, capture_output=True, check=True).stdout
    assert output == render_capacity_csv(source()).encode("utf-8")
    assert b"\r\r\n" not in output
    target = tmp_path / "capacity.csv"
    subprocess.run(args + ["--output", str(target)], capture_output=True, check=True)
    assert target.read_bytes() == output
    assert subprocess.run(args + ["--output", str(target)], capture_output=True).returncode == 2
    assert target.read_bytes() == output
    path.write_bytes(b" " * 65537)
    rejected = tmp_path / "rejected.csv"
    result = subprocess.run(args + ["--output", str(rejected)], capture_output=True)
    assert result.returncode == 2 and not result.stdout and not rejected.exists()


@pytest.mark.parametrize("field,value", [("seeds", list(range(32))), ("steps", 12501)])
def test_capacity_exports_reject_over_budget_plans(field, value):
    data = source().model_dump()
    if field == "steps":
        data["scenario"]["world"]["steps"] = value
    else:
        data[field] = value
    with pytest.raises(ValueError):
        render_capacity_csv(Sweep.model_validate(data))
