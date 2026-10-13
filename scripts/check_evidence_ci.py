"""Create a real failed suite in a retained image, then rerun it in a fresh container."""

import argparse
import json
import subprocess
import uuid
from pathlib import Path

from simweave.bundles import read_bundle
from simweave.provenance import capture
from simweave.rerun import rerun_container
from simweave.suites import Suite, execute_suite, review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    if args.inside:
        suite = Suite.model_validate(
            {
                "name": "Reproducible controller failure",
                "scenarios": [{"name": "Cart recovery"}],
                "seeds": [42],
                "adapters": ["reference", "mujoco", "gazebo"],
                "baseline": {},
                "candidate": {"kp": 0.0, "kd": 0.0},
                "regression_gates": [{"metric": "rmse", "max_increase": 0.02}],
            }
        )
        report = execute_suite(
            suite, args.output, environment=capture(args.source_revision, args.image)
        )
        assert review(report).exit_code == 1
        assert all(c.summary for c in report.cases)
        return
    args.output.mkdir(parents=True, exist_ok=False)
    name = "simweave-evidence-check-" + uuid.uuid4().hex
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--name",
                name,
                "--pull",
                "never",
                "--network",
                "none",
                "--pids-limit",
                "256",
                "--memory",
                "4g",
                "--cpus",
                "2",
                args.image,
                "python",
                "scripts/check_evidence_ci.py",
                "--inside",
                "--image",
                args.image,
                "--source-revision",
                args.source_revision,
                "--output",
                "/tmp/evidence-original",
            ],
            check=True,
            timeout=600,
        )
        subprocess.run(
            ["docker", "cp", name + ":/tmp/evidence-original", str(args.output / "original")],
            check=True,
            timeout=60,
        )
    finally:
        subprocess.run(["docker", "rm", "--force", name], check=True, timeout=60)
    bundle = args.output / "original/evidence.zip"
    manifest, original = read_bundle(bundle)
    assert manifest.environment.source_revision == args.source_revision
    assert len(original.cases) == 6
    assert rerun_container(bundle, args.image, args.output / "rerun") == 0
    verdict = json.loads((args.output / "rerun/reproduction.json").read_text())
    assert verdict["status"] == "reproduced"
    assert verdict["original_exit_code"] == verdict["rerun_exit_code"] == 1
    _, fresh = read_bundle(args.output / "rerun/evidence.zip")
    assert len(fresh.cases) == 6
    print(
        "All six recordings reproduced exactly across fresh containers; failure exit 1 preserved."
    )


if __name__ == "__main__":
    main()
