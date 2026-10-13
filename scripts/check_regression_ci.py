"""Exercise real CLI exit codes and all recordings for passing and degraded controllers."""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from simweave.bundles import read_bundle
from simweave.contracts import Sample
from simweave.engine import verify_recording
from simweave.suites import Suite, SuiteReport, review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision")
    parser.add_argument("--image-id")
    parser.add_argument(
        "--adapters",
        nargs="+",
        choices=["reference", "mujoco", "gazebo"],
        default=["mujoco", "gazebo"],
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "examples/cart-regression.json").read_text())
    data["adapters"] = args.adapters
    args.output.mkdir(parents=True, exist_ok=False)
    for label, expected in (("positive", 0), ("degraded", 1)):
        if label == "degraded":
            data["candidate"].update(kp=0.0, kd=0.0)
        suite = Suite.model_validate(data)
        source = args.output / f"{label}.json"
        source.write_text(suite.model_dump_json(), encoding="utf-8")
        output = args.output / label
        command = [
            sys.executable,
            "-m",
            "simweave.cli",
            "suite",
            str(source),
            "--output",
            str(output),
        ]
        for flag, value in (
            ("--source-revision", args.source_revision),
            ("--image-id", args.image_id),
        ):
            if value:
                command.extend([flag, value])
        completed = subprocess.run(
            command,
            check=False,
        )
        if completed.returncode != expected:
            raise RuntimeError(f"{label} CLI returned {completed.returncode}, expected {expected}")
        report = SuiteReport.model_validate_json((output / "report.json").read_bytes())
        assert len(report.cases) == 20 * len(args.adapters)
        assert review(report).exit_code == expected
        _, bundled = read_bundle(output / "evidence.zip")
        assert bundled == report
        assert (output / "report.html").stat().st_size > 1000
        xml = ET.parse(output / "junit.xml").getroot()
        assert xml.get("errors") == "0"
        assert (int(xml.get("failures")) > 0) == bool(expected)
        for case in report.cases:
            assert case.summary is not None
            assert case.summary.result.passed == (case.role == "baseline" or expected == 0)
            with (output / case.id / "telemetry.jsonl").open(encoding="utf-8") as stream:
                verify_recording(
                    case.scenario,
                    case.summary.result,
                    (Sample.model_validate_json(line) for line in stream),
                )
        print(
            f"{label}: {len(report.cases)} recordings verified; exit {expected} confirmed",
            flush=True,
        )


if __name__ == "__main__":
    main()
