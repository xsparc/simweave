"""Sweep evidence mapping, complete-case summaries and CLI boundaries."""

import json
from statistics import mean

import pytest

from simweave.cli import main
from simweave.suites import SuiteReport, execute_suite, review
from simweave.sweep_review import SweepReview, summarize
from simweave.sweeps import Sweep, plan


def sweep():
    return Sweep.model_validate(
        {
            "name": "review grid",
            "scenario": {"world": {"steps": 10}},
            "axes": [{"field": "robot.mass", "values": [1.0, 2.0]}],
            "seeds": [8, 3],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {"kp": 9.0},
        }
    )


@pytest.fixture
def evidence(tmp_path):
    source = sweep()
    return source, execute_suite(plan(source), tmp_path / "bundle")


def test_point_mapping_metrics_counts_and_stable_identity(evidence):
    source, report = evidence
    result = summarize(source, report)
    assert result == summarize(source, report)
    assert len(result.points) == 2
    assert [p.parameters for p in result.points] == [{"robot.mass": 1.0}, {"robot.mass": 2.0}]
    assert all(p.seeds == [8, 3] for p in result.points)
    pairs = review(report).pairs[:2]
    for metric in result.points[0].metrics:
        values = [next(m for m in p.comparison.metrics if m.metric == metric.metric) for p in pairs]
        assert metric.baseline_mean == mean(v.baseline for v in values)
        assert metric.candidate_mean == mean(v.candidate for v in values)
        assert metric.delta_mean == mean(v.delta for v in values)
        assert metric.delta_min == min(v.delta for v in values)
        assert metric.delta_max == max(v.delta for v in values)
    assert result.exit_code == 1  # Ten steps cannot meet the default final-error gate.
    assert result.points[0].failed_pairs == 2
    assert result.points[0].warnings
    assert SweepReview.model_validate_json(result.model_dump_json()) == result


def test_errors_withhold_entire_point_metrics_not_only_failed_seed(evidence):
    source, report = evidence
    data = report.model_dump()
    data["cases"][0].update(summary=None, error="execution_failed")
    result = summarize(source, SuiteReport.model_validate(data))
    assert result.exit_code == 2
    assert result.points[0].error_pairs == 1
    assert result.points[0].failed_pairs == 1
    assert result.points[0].metrics is None
    assert result.points[1].metrics is not None
    assert result.points[0].seeds == [8, 3]
    assert result.report_digest != summarize(source, report).report_digest


@pytest.mark.parametrize("mutation", ["sweep", "digest", "case_order", "case_missing", "summary"])
def test_mismatched_and_mutated_inputs_rejected(evidence, mutation):
    source, report = evidence
    if mutation == "sweep":
        source.axes[0].values[0] = 1.5
    elif mutation == "digest":
        report = report.model_copy(update={"suite_digest": "0" * 64})
    elif mutation == "case_order":
        report.cases.reverse()
    elif mutation == "case_missing":
        report.cases.pop()
    else:
        report.cases[0].summary.result.metrics["rmse"] = -1.0
    with pytest.raises(ValueError):
        summarize(source, report)


def test_cli_schema_output_bounds_and_no_overwrite(evidence, tmp_path, capsys):
    source, report = evidence
    source_path = tmp_path / "sweep.json"
    report_path = tmp_path / "report.json"
    output = tmp_path / "review.json"
    source_path.write_text(source.model_dump_json(), encoding="utf-8")
    report_path.write_text(report.model_dump_json(), encoding="utf-8")
    assert main(["sweep-review-schema"]) == 0
    assert json.loads(capsys.readouterr().out)["additionalProperties"] is False
    args = ["sweep-review", str(source_path), str(report_path)]
    assert main(args) == 1
    expected = SweepReview.model_validate_json(capsys.readouterr().out)
    assert main(args + ["--output", str(output)]) == 1
    original = output.read_bytes()
    assert SweepReview.model_validate_json(original) == expected
    assert main(args + ["--output", str(output)]) == 2
    assert output.read_bytes() == original
    report_path.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    rejected = tmp_path / "rejected.json"
    assert main(args + ["--output", str(rejected)]) == 2
    assert not rejected.exists()
    report_path.write_text(report.model_dump_json(), encoding="utf-8")
    source_path.write_bytes(b" " * 65537)
    assert main(args) == 2
    assert capsys.readouterr().out == ""


def test_success_and_multiple_adapters_remain_separate(tmp_path):
    pytest.importorskip("mujoco")
    data = sweep().model_dump()
    data["adapters"] = ["reference", "mujoco"]
    data["scenario"]["gates"] = [{"metric": "final_error", "op": "lte", "threshold": 10.0}]
    source = Sweep.model_validate(data)
    result = summarize(source, execute_suite(plan(source), tmp_path / "both"))
    assert result.exit_code == 0
    assert [p.adapter for p in result.points] == ["reference", "mujoco"] * 2
    assert all(p.passed_pairs == 2 and p.error_pairs == 0 for p in result.points)
    assert all(p.metrics is not None for p in result.points)
