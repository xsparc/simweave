"""Versioned long-form sweep export; validate before emitting any CSV."""

import csv
import io

from simweave.contracts import canonical
from simweave.suites import SuiteReport
from simweave.sweep_review import summarize
from simweave.sweeps import Sweep

FIELDS = (
    "schema_version",
    "sweep_name_text",
    "scenario_text",
    "adapter",
    "parameters_json",
    "seeds_json",
    "passed_pairs",
    "failed_pairs",
    "error_pairs",
    "metric",
    "baseline_mean",
    "candidate_mean",
    "delta_mean",
    "delta_min",
    "delta_max",
    "warnings_json",
    "suite_sha256",
    "sweep_sha256",
    "report_sha256",
    "exit_code",
    "interpretation",
)


def render_sweep_csv(sweep: Sweep, report: SuiteReport) -> tuple[str, int]:
    """Preserve full numeric precision and explicit rows for incomplete points.

    Free-text labels receive a literal text: prefix; JSON cells start with { or [.
    Quoting alone does not protect spreadsheets from formula interpretation.
    """
    result = summarize(sweep, report)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(FIELDS)
    for point in result.points:
        metrics = {metric.metric: metric for metric in point.metrics or []}
        for name in ("final_error", "rmse", "max_abs_position", "control_effort"):
            metric = metrics.get(name)
            values = (
                [
                    metric.baseline_mean,
                    metric.candidate_mean,
                    metric.delta_mean,
                    metric.delta_min,
                    metric.delta_max,
                ]
                if metric
                else [""] * 5
            )
            writer.writerow(
                [
                    1,
                    "text:" + sweep.name,
                    "text:" + point.scenario,
                    point.adapter,
                    canonical(point.parameters),
                    canonical(point.seeds),
                    point.passed_pairs,
                    point.failed_pairs,
                    point.error_pairs,
                    name,
                    *values,
                    canonical(point.warnings),
                    result.suite_digest,
                    result.sweep_digest,
                    result.report_digest,
                    result.exit_code,
                    result.interpretation,
                ]
            )
    return stream.getvalue(), result.exit_code
