"""Portable CLI with machine-readable outputs and useful exit codes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from simweave.contracts import RunResult, Sample, Scenario, canonical
from simweave.engine import execute, verify_recording


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="simweave")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="write an example scenario")
    init.add_argument("path", type=Path)
    commands.add_parser("schema", help="print the scenario JSON Schema")
    validate = commands.add_parser("validate", help="validate a scenario")
    validate.add_argument("path", type=Path)
    run = commands.add_parser("run", help="run an experiment locally")
    run.add_argument("path", type=Path)
    run.add_argument("--output", required=True, type=Path)
    replay = commands.add_parser("replay", help="verify recorded telemetry and gates")
    replay.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            with args.path.open("x", encoding="utf-8") as stream:
                stream.write(Scenario().model_dump_json(indent=2) + "\n")
            return 0
        if args.command == "schema":
            print(json.dumps(Scenario.model_json_schema(), indent=2))
            return 0
        if args.command == "replay":
            scenario = Scenario.model_validate_json((args.path / "scenario.json").read_bytes())
            result = RunResult.model_validate_json((args.path / "result.json").read_bytes())
            with (args.path / "telemetry.jsonl").open(encoding="utf-8") as stream:
                verify_recording(
                    scenario, result, (Sample.model_validate_json(line) for line in stream)
                )
            print(canonical({"verified": True, "passed": result.passed}))
            return 0 if result.passed else 1
        scenario = Scenario.model_validate_json(args.path.read_bytes())
        if args.command == "validate":
            print(canonical({"valid": True, "scenario_digest": scenario.digest()}))
            return 0
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "scenario.json").write_text(
            scenario.model_dump_json(indent=2), encoding="utf-8"
        )
        with (args.output / "telemetry.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
            result = execute(scenario, lambda s: stream.write(canonical(s.model_dump()) + "\n"))
        (args.output / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(result.model_dump_json())
        return 0 if result.passed else 1
    except (OSError, ValueError, ValidationError, ImportError) as exc:
        # Avoid leaking filesystem paths or raw input in diagnostics.
        print(
            canonical(
                {
                    "error": type(exc).__name__,
                    "message": "Operation failed; check input, dependencies, and output path.",
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
