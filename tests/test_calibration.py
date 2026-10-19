import itertools
import json
import random

import pytest
from pydantic import ValidationError

from simweave.calibration import CalibrationConfig, calibrate, frequency
from simweave.cli import main
from simweave.statistics import DecisionPolicy, Interval, interval_verdict, paired_interval


@pytest.mark.parametrize(
    "changes",
    [
        {"trials": 0},
        {"trials": 1001},
        {"trials": True},
        {"resamples": 999},
        {"resamples": 5001},
        {"random_seed": -1},
        {"extra": 1},
    ],
)
def test_calibration_bounds(changes):
    with pytest.raises(ValidationError):
        CalibrationConfig.model_validate(changes)


def test_frequency_matches_hand_calculation():
    assert frequency(25, 100) == {
        "count": 25,
        "rate": 0.25,
        "monte_carlo_se": (0.25 * 0.75 / 100) ** 0.5,
    }


def test_seeded_calibration_is_repeatable_and_counts_all_trials():
    config = CalibrationConfig(trials=8)
    random.seed(55)
    before = random.getstate()
    report = calibrate(config)
    assert random.getstate() == before
    assert report == calibrate(config)
    for cohort in report["cohorts"]:
        assert sum(v["count"] for v in cohort["verdicts"].values()) == config.trials
        assert 0 <= cohort["mean_coverage"]["rate"] <= 1
        assert len(cohort["input_sha256"]) == 64
    assert report["cohorts"][2]["verdicts"]["regression"]["rate"] > 0.5
    assert report["cohorts"][0]["regression_interpretation"] == "false_positive_rate"
    assert report["cohorts"][2]["regression_interpretation"] == "power"
    other = calibrate(CalibrationConfig(trials=8, random_seed=1))
    assert report["cohorts"][0]["input_sha256"] != other["cohorts"][0]["input_sha256"]


def test_independent_two_point_distribution(monkeypatch):
    # Enumerate all equally likely size-two resamples independently of the bootstrap.
    values = [-1.0, 1.0]
    exact = sorted(sum(pair) / 2 for pair in itertools.product(values, repeat=2))
    draws = itertools.cycle([0.0, 0.0, 0.0, 0.99, 0.99, 0.0, 0.99, 0.99])
    monkeypatch.setattr(random.Random, "random", lambda self: next(draws))
    policy = DecisionPolicy(metrics=[{"metric": "rmse", "max_increase": 0.0}], resamples=1000)
    result = paired_interval(values, policy)
    assert result.mean == sum(exact) / len(exact)
    assert (result.low, result.high) == (exact[0], exact[-1])


def test_classification_preserves_boundaries_and_ineligible_population():
    interval = Interval(mean=0.1, low=0.0, high=0.2, constant=False)
    assert interval_verdict(interval, -0.1) == "regression"
    assert interval_verdict(interval, 0.0) == "inconclusive"
    assert interval_verdict(interval, 0.2) == "within_tolerance"
    assert interval_verdict(interval, 0.2, eligible=False) == "inconclusive"
    assert (
        interval_verdict(Interval(mean=1.0, low=1.0, high=1.0, constant=True), 0.0)
        == "inconclusive"
    )


def test_cli_emits_versioned_report_and_rejects_unbounded_work(capsys):
    assert main(["calibrate", "--trials", "1"]) == 0
    assert len(json.loads(capsys.readouterr().out)["cohorts"]) == 4
    assert main(["calibrate", "--trials", "1001"]) == 2
    assert capsys.readouterr().out == ""
