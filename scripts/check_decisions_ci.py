"""Real 30-seed decisions and 20 recorded candidates against one pinned approval."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from simweave.bundles import read_bundle
from simweave.provenance import capture
from simweave.statistics import DecisionPolicy
from simweave.suites import Suite, execute_suite


def cli(*args, expected=0):
    completed = subprocess.run(
        [sys.executable, "-m", "simweave.cli", *(str(a) for a in args)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != expected:
        raise RuntimeError(f"CLI {args[0]} returned {completed.returncode}, expected {expected}")
    return json.loads(completed.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--adapters",
        choices=["reference", "mujoco", "gazebo"],
        nargs="+",
        default=["reference", "mujoco"],
    )
    parser.add_argument("--history-builds", type=int, choices=[0, 20], default=20)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--image-id")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    environment = capture(args.source_revision, args.image_id)
    policy = DecisionPolicy.model_validate({"metrics": [{"metric": "rmse", "max_increase": 0.02}]})
    policy_path = args.output / "policy.json"
    policy_path.write_text(policy.model_dump_json(), encoding="utf-8")

    def record(adapter, kp, destination):
        suite = Suite.model_validate(
            {
                "name": "Thirty-seed recovery",
                "scenarios": [
                    {"name": "Noisy cart recovery", "sensors": {"position_noise_std": 0.03}}
                ],
                "seeds": list(range(30)),
                "adapters": [adapter],
                "baseline": {},
                "candidate": {"kp": kp, "kd": 0.0 if kp == 0 else 4.0},
            }
        )
        execute_suite(suite, destination, environment=environment)
        bundle = destination / "evidence.zip"
        _, restored = read_bundle(bundle)
        assert len(restored.cases) == 60 and all(c.summary for c in restored.cases)
        return bundle

    for adapter in args.adapters:
        for kind, kp, expected in (("positive", 8.1, 0), ("degraded", 0.0, 1)):
            bundle = record(adapter, kp, args.output / f"{adapter}-{kind}")
            decision_args = ["statistics", bundle, "--policy", policy_path]
            result = cli(
                *decision_args,
                "--output",
                args.output / f"{adapter}-{kind}-decision",
                expected=expected,
            )
            repeat = cli(
                *decision_args,
                "--output",
                args.output / f"{adapter}-{kind}-repeat",
                expected=expected,
            )
            assert result == repeat
            group = result["groups"][0]
            assert group["complete_pairs"] == 30
            assert group["metrics"][0]["verdict"] == (
                "regression" if expected else "within_tolerance"
            )
            print(
                f"{adapter}: 30 paired seeds, {kind}, reproducible decision exit {expected}.",
                flush=True,
            )

    if args.history_builds:
        database = args.output / "history.sqlite3"
        shared = ["--database", database]
        cli("history", "init", *shared)
        base_bundle = args.output / "reference-positive/evidence.zip"
        if not base_bundle.exists():
            base_bundle = record("reference", 8.1, args.output / "reference-baseline")
        base = cli(
            "history", "add", base_bundle, *shared, "--build", "approved", "--role", "baseline"
        )
        first = cli(
            "history",
            "promote",
            "approved",
            *shared,
            "--policy",
            policy_path,
            "--expected-generation",
            "0",
            "--approved-by",
            "ci-synthetic-reviewer",
            "--reason",
            "Synthetic test baseline; not a production approval",
        )
        for index in range(1, args.history_builds + 1):
            label = f"candidate-{index:02d}"
            bundle = record("reference", 8.0 + index / 100, args.output / label)
            cli("history", "add", bundle, *shared, "--build", label)
            result = cli(
                "history",
                "compare",
                label,
                *shared,
                "--generation",
                "1",
                "--output",
                args.output / f"{label}-decision",
            )
            assert result["baseline_digest"] == base["digest"]
            assert (
                result["baseline_generation"] == 1
                and result["statistics"]["policy"] == first["policy"]
            )
        cli(
            "history",
            "promote",
            "candidate-20",
            *shared,
            "--policy",
            policy_path,
            "--expected-generation",
            "1",
            "--approved-by",
            "ci-synthetic-reviewer",
            "--reason",
            "Synthetic promotion test",
        )
        cli(
            "history",
            "rollback",
            *shared,
            "--to-generation",
            "1",
            "--expected-generation",
            "2",
            "--approved-by",
            "ci-synthetic-reviewer",
            "--reason",
            "Synthetic rollback test",
        )
        cli("history", "show", *shared, "--output", args.output / "history-review")
        data = json.loads((args.output / "history-review/history.json").read_text())
        assert data["generation"] == 3 and data["active_baseline"] == "approved"
        assert len(data["comparisons"]) == 20 and len(data["builds"]) == 21
        assert data["events"][2]["build_digest"] == data["events"][0]["build_digest"]
        print(
            "20 independently recorded controller candidates compared to approval 1; "
            "promotion and rollback verified.",
            flush=True,
        )


if __name__ == "__main__":
    main()
