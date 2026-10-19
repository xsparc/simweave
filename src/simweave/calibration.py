"""Synthetic marginal calibration, independent of simulators, HTTP and persistence."""

from __future__ import annotations

import hashlib
import math
import random

from pydantic import Field

from simweave.contracts import canonical
from simweave.statistics import DecisionPolicy, Versioned, interval_verdict, paired_interval


class CalibrationConfig(Versioned):
    trials: int = Field(default=1000, ge=1, le=1000)
    resamples: int = Field(default=1000, ge=1000, le=5000)
    random_seed: int = Field(default=1937, ge=0, le=2**32 - 1)


def frequency(count: int, trials: int) -> dict:
    """Binomial Monte Carlo standard error, not an interval-coverage guarantee."""
    rate = count / trials
    return {"count": count, "rate": rate, "monte_carlo_se": math.sqrt(rate * (1 - rate) / trials)}


def calibrate(config: CalibrationConfig) -> dict:
    config = CalibrationConfig.model_validate(config.model_dump())
    policy = DecisionPolicy.model_validate(
        {
            "metrics": [{"metric": "rmse", "max_increase": 0.1}],
            "resamples": config.resamples,
            "random_seed": 1729,
        }
    )
    cohorts = []
    # Independent draws for each cohort; exactly 30 paired metric differences.
    for offset, (name, mean, tolerance, skewed) in enumerate(
        [
            ("normal_null", 0.0, 0.0, False),
            ("normal_boundary", 0.1, 0.1, False),
            ("normal_shifted", 1.0, 0.1, False),
            ("skewed_null", 0.0, 0.0, True),
        ]
    ):
        rng = random.Random(config.random_seed + offset)
        counts = {"regression": 0, "within_tolerance": 0, "inconclusive": 0}
        covered = 0
        inputs = hashlib.sha256()
        for _ in range(config.trials):
            differences = [
                rng.expovariate(1.0) - 1.0 if skewed else rng.gauss(mean, 1.0) for _ in range(30)
            ]
            inputs.update((canonical(differences) + "\n").encode())
            interval = paired_interval(differences, policy)
            counts[interval_verdict(interval, tolerance)] += 1
            covered += int(interval.low <= mean <= interval.high)
        cohorts.append(
            {
                "name": name,
                "distribution": "centered_exponential" if skewed else "normal",
                "population_mean": mean,
                "population_std": 1.0,
                "max_increase": tolerance,
                "pairs": 30,
                "trials": config.trials,
                "input_sha256": inputs.hexdigest(),
                "regression_interpretation": "power" if mean > tolerance else "false_positive_rate",
                "verdicts": {key: frequency(value, config.trials) for key, value in counts.items()},
                "mean_coverage": frequency(covered, config.trials),
            }
        )
    return {
        "schema_version": 1,
        "algorithm": "paired-percentile-mean-v1",
        "generator": "python-random-gauss-expovariate-v1",
        "config": config.model_dump(),
        "bootstrap_seed": policy.random_seed,
        "nominal_marginal_coverage": 0.95,
        "cohorts": cohorts,
        "warnings": [
            "Synthetic independent differences are not simulator calibration or evidence bundles.",
            "Observed rates apply only to these distributions, pair counts and resampling policy.",
            "No multiple-metric or repeated-build correction; no automatic baseline approval.",
            "Monte Carlo standard errors describe simulation frequency uncertainty only.",
        ],
    }
