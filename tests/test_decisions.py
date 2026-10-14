import itertools
import json
import math
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from simweave import history, statistics
from simweave.cli import main
from simweave.contracts import canonical
from simweave.decision_reports import render_statistics
from simweave.provenance import capture
from simweave.statistics import DecisionPolicy, Interval, analyze, paired_interval
from simweave.suites import Suite, SuiteReport, execute_suite


def policy(**changes):
    return DecisionPolicy.model_validate(
        {"metrics": [{"metric": "rmse", "max_increase": 0.02}], "resamples": 1000, **changes}
    )


def suite(**changes):
    return Suite.model_validate(
        {
            "name": "Paired recovery",
            "scenarios": [
                {
                    "name": "Cart",
                    "world": {"steps": 100},
                    "sensors": {"position_noise_std": 0.05},
                    "gates": [{"metric": "rmse", "threshold": 2.0}],
                }
            ],
            "seeds": list(range(30)),
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {"kp": 8.1},
            **changes,
        }
    )


@pytest.fixture(scope="module")
def recording(tmp_path_factory):
    root = tmp_path_factory.mktemp("decisions")
    report = execute_suite(suite(), root / "runs")
    return root / "runs/evidence.zip", report


@pytest.fixture
def catalog(tmp_path, recording, monkeypatch):
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    path = tmp_path / "history.sqlite3"
    history.initialize(path)
    history.add_build(path, recording[0], "baseline", "baseline")
    history.add_build(path, recording[0], "candidate")
    return path


def approval(generation=0, **changes):
    return history.Approval(
        expected_generation=generation,
        approved_by="test-reviewer",
        reason="Synthetic approval",
        **changes,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": True},
        {"resamples": 10001},
        {"resamples": True},
        {"random_seed": -1},
        {"extra": 1},
        {"metrics": []},
        {"metrics": [{"metric": "rmse", "max_increase": float("nan")}]},
        {"metrics": [{"metric": "rmse", "max_increase": 0.0}] * 2},
    ],
)
def test_closed_bounded_policy(changes):
    with pytest.raises(ValidationError):
        policy(**changes)


def test_independent_exact_resampling_distribution(monkeypatch):
    # Every size-two replacement sample has equal weight: [-1,-1],[-1,1],[1,-1],[1,1].
    draws = itertools.cycle([0.0, 0.0, 0.0, 0.99, 0.99, 0.0, 0.99, 0.99])
    monkeypatch.setattr(statistics.random.Random, "random", lambda self: next(draws))
    interval = paired_interval([-1.0, 1.0], policy())
    assert interval == Interval(mean=0.0, low=-1.0, high=1.0, constant=False)
    assert statistics._quantile([0.0, 10.0, 20.0, 30.0], 0.25) == 7.5


def test_seeded_interval_symmetry_shift_and_global_rng_isolation():
    data = [i / 100 for i in range(-15, 15)]
    p = policy()
    statistics.random.seed(999)
    expected = statistics.random.random()
    statistics.random.seed(999)
    first = paired_interval(data, p)
    assert statistics.random.random() == expected
    assert first == paired_interval(data, p)
    assert first.mean == pytest.approx(-0.005)
    assert first.low < first.mean < first.high
    shifted = paired_interval([x + 2 for x in data], p)
    assert shifted.low == pytest.approx(first.low + 2)
    assert shifted.high == pytest.approx(first.high + 2)
    assert paired_interval(data, policy(random_seed=2)) != first


@pytest.mark.parametrize("data", [[], [1.0] * 33, [float("inf")], [float("nan")]])
def test_invalid_interval_data(data):
    with pytest.raises(ValueError):
        paired_interval(data, policy())


def test_floating_point_degenerate_bootstrap_is_flagged():
    interval = paired_interval([0.0, 5e-324] * 15, policy())
    assert interval.constant and interval.low == interval.high == 0.0


def test_thirty_real_pairs_repeat_and_seed_order_does_not_change_result(recording):
    _, report = recording
    result = analyze(report, report, policy())
    assert result.exit_code == 0
    assert result.groups[0].complete_pairs == 30
    assert result == analyze(report, report, policy())
    data = report.model_dump()
    data["suite"]["seeds"].reverse()
    changed = Suite.model_validate(data["suite"])
    mapping = {(c.scenario.seed, c.role): c for c in report.cases}
    data["suite_digest"] = changed.digest()
    data["cases"] = [
        {**mapping[(scenario.seed, role)].model_dump(), "id": identifier}
        for identifier, role, scenario in changed.expand()
    ]
    reordered = SuiteReport.model_validate(data)
    assert analyze(reordered, reordered, policy()).groups == result.groups


@pytest.mark.parametrize(
    "low,high,verdict",
    [
        (0.021, 0.03, "regression"),
        (0.01, 0.02, "within_tolerance"),
        (0.02, 0.03, "inconclusive"),
        (-0.1, 0.03, "inconclusive"),
    ],
)
def test_practical_threshold_boundaries(recording, monkeypatch, low, high, verdict):
    monkeypatch.setattr(
        statistics,
        "paired_interval",
        lambda *args: Interval(mean=(low + high) / 2, low=low, high=high, constant=False),
    )
    result = analyze(recording[1], recording[1], policy())
    assert result.status == verdict


def test_constant_and_singleton_are_not_certainty(recording, tmp_path):
    report = recording[1]
    result = analyze(report, report, policy(), baseline_role="candidate")
    assert result.status == "inconclusive"
    assert result.groups[0].metrics[0].interval.constant
    single = execute_suite(suite(seeds=[1]), tmp_path / "single")
    result = analyze(single, single, policy())
    assert result.exit_code == 2
    assert "30 complete" in result.groups[0].issues[0]
    assert paired_interval([1e308] * 30, policy()).mean == pytest.approx(1e308)


def test_missing_pair_never_emits_survivor_interval(recording):
    data = recording[1].model_dump()
    data["cases"][1].update(summary=None, error="execution_failed")
    report = SuiteReport.model_validate(data)
    result = analyze(report, report, policy())
    assert result.exit_code == 2
    assert result.groups[0].complete_pairs == 29
    assert result.groups[0].metrics[0].interval is None


def test_mismatched_seed_populations_and_physics_are_inconclusive(recording, tmp_path):
    other = execute_suite(suite(seeds=list(range(1, 31))), tmp_path / "shifted-seeds")
    result = analyze(recording[1], other, policy())
    assert result.status == "inconclusive"
    assert result.groups[0].seeds == list(range(31))
    assert result.groups[0].metrics[0].interval is None
    changed = execute_suite(suite(scenarios=[{"name": "Cart"}]), tmp_path / "physics")
    result = analyze(recording[1], changed, policy())
    assert result.groups[0].complete_pairs == 0
    assert result.groups[0].metrics[0].interval is None


def test_runtime_change_is_inconclusive_code_revision_is_not(recording):
    env = capture()
    changed = env.model_copy(
        update={"source_revision": "a" * 40, "implementation_digest": "b" * 64}
    )
    assert analyze(recording[1], recording[1], policy(), environments=(env, changed)).exit_code == 0
    changed = env.model_copy(update={"python": "3.11.0"})
    assert analyze(recording[1], recording[1], policy(), environments=(env, changed)).exit_code == 2


def test_quality_failure_is_never_overridden_by_statistics(tmp_path):
    report = execute_suite(
        suite(
            scenarios=[
                {
                    "name": "Cart",
                    "world": {"steps": 10},
                    "gates": [{"metric": "rmse", "threshold": 0.0}],
                }
            ],
        ),
        tmp_path / "failed",
    )
    result = analyze(report, report, policy(metrics=[{"metric": "rmse", "max_increase": 100.0}]))
    assert result.exit_code == 1
    assert result.groups[0].quality_failures == 60


def test_individual_gates_remain_binding(recording):
    data = recording[1].model_dump()
    data["suite"]["regression_gates"] = [{"metric": "control_effort", "max_increase": 0.0}]
    data["suite_digest"] = Suite.model_validate(data["suite"]).digest()
    report = SuiteReport.model_validate(data)
    result = analyze(report, report, policy(), individual_gates=True)
    assert result.exit_code == 1
    assert result.groups[0].individual_regression_failures > 0


def test_scenarios_are_not_pooled_to_reach_thirty_seeds(tmp_path):
    scenarios = [
        {
            "name": name,
            "world": {"steps": 10},
            "sensors": {"position_noise_std": 0.05},
            "gates": [{"metric": "rmse", "threshold": 2.0}],
        }
        for name in ("Cart A", "Cart B")
    ]
    report = execute_suite(suite(scenarios=scenarios, seeds=list(range(15))), tmp_path / "groups")
    result = analyze(report, report, policy())
    assert [g.complete_pairs for g in result.groups] == [15, 15]
    assert result.exit_code == 2


def test_failed_baseline_cannot_be_promoted(catalog, tmp_path):
    failed = execute_suite(
        suite(
            scenarios=[
                {
                    "name": "Cart",
                    "world": {"steps": 10},
                    "gates": [{"metric": "rmse", "threshold": 0.0}],
                }
            ],
        ),
        tmp_path / "failed-promotion",
    )
    assert not failed.cases[1].summary.result.passed
    history.add_build(catalog, tmp_path / "failed-promotion/evidence.zip", "failed")
    with pytest.raises(ValueError, match="passing quality"):
        history.change_baseline(catalog, approval(), build="failed", policy=policy())
    assert history.snapshot(catalog)["generation"] == 0


def test_catalog_immutable_approval_rollback_and_restart(catalog):
    first = history.change_baseline(catalog, approval(), build="baseline", policy=policy())
    compared = history.compare_build(catalog, "candidate")
    assert compared.statistics.exit_code == 0
    assert compared.baseline_generation == 1
    assert compared.statistics.baseline_report_digest == compared.statistics.candidate_report_digest
    assert compared.statistics.baseline_environment is not None
    second = history.change_baseline(
        catalog, approval(1), build="candidate", policy=policy(random_seed=6)
    )
    restored = history.change_baseline(catalog, approval(2), restore=1)
    assert (first.generation, second.generation, restored.generation) == (1, 2, 3)
    assert restored.build == "baseline" and restored.policy == first.policy
    assert restored.action == "rollback" and restored.restored_generation == 1
    assert history.compare_build(catalog, "candidate", 1) == compared
    reopened = history.snapshot(catalog)
    assert reopened["generation"] == 3
    assert reopened["active_baseline"] == "baseline"
    assert reopened["comparisons"][0] == compared.model_dump()
    with sqlite3.connect(catalog) as connection:
        for table in ("builds", "events", "comparisons"):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(f"DELETE FROM {table}")


def test_concurrent_approvals_exactly_one_commits(catalog):
    def promote(label):
        try:
            return history.change_baseline(catalog, approval(), build=label, policy=policy())
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(promote, ["baseline", "candidate"]))
    assert sum(r is not None for r in results) == 1
    assert history.snapshot(catalog)["generation"] == 1


def test_invalid_operations_do_not_change_catalog(catalog, recording, tmp_path):
    before = history.snapshot(catalog)
    with pytest.raises(sqlite3.IntegrityError):
        history.add_build(catalog, recording[0], "baseline")
    with pytest.raises(ValueError):
        history.change_baseline(catalog, approval(1), build="candidate", policy=policy())
    with pytest.raises(ValueError):
        history.change_baseline(catalog, approval(), restore=999)
    with pytest.raises(ValueError):
        history.compare_build(catalog, "candidate")
    with pytest.raises(FileExistsError):
        history.initialize(catalog)
    damaged = tmp_path / "bad.zip"
    damaged.write_bytes(b"invalid")
    with pytest.raises(ValueError):
        history.add_build(catalog, damaged, "bad")
    assert history.snapshot(catalog) == before


def test_corrupt_catalog_rejected(catalog):
    with sqlite3.connect(catalog) as connection:
        connection.execute("DROP TRIGGER immutable_builds_UPDATE")
        connection.execute("UPDATE builds SET digest=? WHERE label=?", ("0" * 64, "baseline"))
    with pytest.raises(ValueError, match="integrity"):
        history.snapshot(catalog)


def test_catalog_limits(catalog, recording, monkeypatch):
    monkeypatch.setattr(history, "MAX_BUILDS", 2)
    with pytest.raises(ValueError, match="build limit"):
        history.add_build(catalog, recording[0], "third")
    history.change_baseline(catalog, approval(), build="baseline", policy=policy())
    monkeypatch.setattr(history, "MAX_EVENTS", 1)
    with pytest.raises(ValueError, match="event limit"):
        history.change_baseline(catalog, approval(1), restore=1)
    monkeypatch.setattr(history, "MAX_COMPARISONS", 0)
    with pytest.raises(ValueError, match="comparison limit"):
        history.compare_build(catalog, "candidate")


def test_public_cli_and_escaped_script_free_reports(catalog, recording, tmp_path, capsys):
    p = tmp_path / "policy.json"
    p.write_text(policy().model_dump_json())
    assert main(["statistics-schema"]) == 0
    assert json.loads(capsys.readouterr().out)["additionalProperties"] is False
    args = [
        "statistics",
        str(recording[0]),
        "--policy",
        str(p),
        "--output",
        str(tmp_path / "stats"),
    ]
    assert main(args) == 0
    capsys.readouterr()
    assert main(args) == 2
    assert "Operation failed" in capsys.readouterr().err
    shared = ["--database", str(catalog)]
    assert (
        main(
            [
                "history",
                "promote",
                "baseline",
                *shared,
                "--policy",
                str(p),
                "--expected-generation",
                "0",
                "--approved-by",
                "reviewer",
                "--reason",
                "<script>alert(1)</script>",
            ]
        )
        == 0
    )
    assert (
        main(["history", "compare", "candidate", *shared, "--output", str(tmp_path / "comparison")])
        == 0
    )
    assert main(["history", "show", *shared, "--output", str(tmp_path / "history")]) == 0
    page = (tmp_path / "history/report.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page and "<script>" not in page
    data = json.loads((tmp_path / "comparison/decision.json").read_text())
    assert data["baseline_generation"] == 1 and data["candidate_build"] == "candidate"
    result = analyze(recording[1], recording[1], policy())
    page = render_statistics(result)
    assert "script-src &#x27;none&#x27;" in page
    assert "30 complete pairs" in page and "95% interval" in page
    assert math.isfinite(
        json.loads(canonical(result.model_dump()))["groups"][0]["metrics"][0]["interval"]["mean"]
    )
