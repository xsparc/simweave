"""CSV identity, precision, incomplete evidence and untrusted-cell boundaries."""

import csv
import io
import json
import subprocess
import sys

import pytest

from simweave.cli import main
from simweave.suites import SuiteReport, execute_suite
from simweave.sweep_csv import FIELDS, render_sweep_csv
from simweave.sweep_review import summarize
from simweave.sweeps import Sweep, plan


@pytest.fixture
def evidence(tmp_path):
    source = Sweep.model_validate(
        {
            "name": '=HYPERLINK("bad")\r\n,＠test',
            "scenario": {"name": '+formula,"quoted"\nnext', "world": {"steps": 10}},
            "axes": [{"field": "robot.mass", "values": [1.0, 2.0]}],
            "seeds": [8, 3],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {"kp": 9.0},
        }
    )
    return source, execute_suite(plan(source), tmp_path / "bundle")


def rows(output):
    return list(csv.DictReader(io.StringIO(output, newline="")))


def test_roundtrip_precision_identity_and_safe_text(evidence):
    source, report = evidence
    output, code = render_sweep_csv(source, report)
    assert (output, code) == render_sweep_csv(source, report)
    assert code == 1
    exported = rows(output)
    assert len(exported) == 8
    assert tuple(exported[0]) == FIELDS
    summary = summarize(source, report)
    for row, metric in zip(exported, [m for p in summary.points for m in p.metrics], strict=True):
        assert row["sweep_name_text"] == "text:" + source.name
        assert row["scenario_text"].startswith("text:+formula")
        assert row["report_sha256"] == summary.report_digest
        assert row["metric"] == metric.metric
        for name in ("baseline_mean", "candidate_mean", "delta_mean", "delta_min", "delta_max"):
            assert float(row[name]) == getattr(metric, name)
        assert json.loads(row["seeds_json"]) == [8, 3]
        assert json.loads(row["warnings_json"])
    assert json.loads(exported[4]["parameters_json"]) == {"robot.mass": 2.0}


def test_incomplete_points_keep_rows_and_blank_all_metrics(evidence):
    source, report = evidence
    data = report.model_dump()
    data["cases"][0].update(summary=None, error="execution_failed")
    output, code = render_sweep_csv(source, SuiteReport.model_validate(data))
    assert code == 2
    exported = rows(output)
    assert len(exported) == 8
    for row in exported[:4]:
        assert row["error_pairs"] == "1"
        assert all(row[name] == "" for name in FIELDS[10:15])
        assert "withheld" in row["warnings_json"]
    assert all(row["baseline_mean"] for row in exported[4:])


def test_cli_output_and_rejection_before_write(evidence, tmp_path, capsys):
    source, report = evidence
    sweep_path, report_path = tmp_path / "sweep.json", tmp_path / "report.json"
    sweep_path.write_text(source.model_dump_json(), encoding="utf-8")
    report_path.write_text(report.model_dump_json(), encoding="utf-8")
    args = ["sweep-review", str(sweep_path), str(report_path), "--format", "csv"]
    assert main(args) == 1
    assert len(rows(capsys.readouterr().out)) == 8
    output = tmp_path / "review.csv"
    assert main(args + ["--output", str(output)]) == 1
    original = output.read_bytes()
    assert b"\r\n" in original and b"\r\r\n" not in original
    assert main(args + ["--output", str(output)]) == 2
    assert output.read_bytes() == original
    report_path.write_text(
        report.model_copy(update={"suite_digest": "0" * 64}).model_dump_json(), encoding="utf-8"
    )
    rejected = tmp_path / "bad.csv"
    assert main(args + ["--output", str(rejected)]) == 2
    assert not rejected.exists()


def test_real_cli_stdout_is_utf8_with_exact_csv_bytes(evidence, tmp_path):
    source, report = evidence
    sweep_path, report_path = tmp_path / "sweep.json", tmp_path / "report.json"
    sweep_path.write_text(source.model_dump_json(), encoding="utf-8")
    report_path.write_text(report.model_dump_json(), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from simweave.cli import main; raise SystemExit(main())",
            "sweep-review",
            str(sweep_path),
            str(report_path),
            "--format",
            "csv",
        ],
        capture_output=True,
        check=False,
    )
    expected, code = render_sweep_csv(source, report)
    assert result.returncode == code
    assert result.stdout == expected.encode("utf-8")
    assert not result.stderr
