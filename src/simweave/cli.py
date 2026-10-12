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
    serve = commands.add_parser("serve", help="start the authenticated HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    demo = commands.add_parser("demo", help="start the local dashboard, API, and worker")
    demo.add_argument("--port", type=int, default=8000)
    demo.add_argument("--database", type=Path, default=Path(".simweave/demo.sqlite3"))
    worker = commands.add_parser("worker", help="consume durable simulation jobs")
    worker.add_argument("--database", type=Path)
    worker.add_argument("--once", action="store_true")
    ros = commands.add_parser("ros2", help="control an existing ROS 2 simulator")
    ros.add_argument("action", choices=["features", "reset", "step"])
    ros.add_argument("--namespace", default="/gzserver")
    ros.add_argument("--steps", type=int, default=1)
    ros.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            import multiprocessing
            import secrets

            import uvicorn

            from simweave.api import create_app
            from simweave.config import Settings
            from simweave.store import Store
            from simweave.worker import work_forever

            token = secrets.token_urlsafe(32)
            settings = Settings(args.database, {token: "demo"})
            app = create_app(settings)
            process = multiprocessing.get_context("spawn").Process(
                target=work_forever, args=(Store(args.database),), daemon=True
            )
            process.start()
            print(f"Dashboard: http://127.0.0.1:{args.port}/#token={token}", flush=True)
            print("Local demo token lasts for this server session. Press Ctrl+C to stop.")
            try:
                uvicorn.run(app, host="127.0.0.1", port=args.port)
            finally:
                process.terminate()
                process.join(timeout=5)
            return 0
        if args.command == "serve":
            import uvicorn

            from simweave.api import create_app

            uvicorn.run(create_app(), host=args.host, port=args.port)
            return 0
        if args.command == "worker":
            import os

            from simweave.store import Store
            from simweave.worker import work_forever, work_once

            store = Store(
                args.database or Path(os.environ.get("SIMWEAVE_DB", ".simweave/runs.sqlite3"))
            )
            work_once(store) if args.once else work_forever(store)
            return 0
        if args.command == "ros2":
            from simweave.adapters.ros2 import RclpyTransport, RosControl

            transport = RclpyTransport(args.namespace)
            try:
                control = RosControl(transport, args.timeout)
                if args.action == "features":
                    print(canonical({"features": sorted(control.features())}))
                elif args.action == "reset":
                    control.reset()
                    print(canonical({"reset": True}))
                else:
                    control.step(args.steps)
                    print(canonical({"stepped": args.steps}))
            finally:
                transport.close()
            return 0
        if args.command == "init":
            with args.path.open("x", encoding="utf-8") as stream:
                stream.write(Scenario().model_dump_json(indent=2) + "\n")
            return 0
        if args.command == "schema":
            print(json.dumps(Scenario.model_json_schema(), indent=2))
            return 0
        if args.command == "replay":
            if args.path.is_file():
                with args.path.open(encoding="utf-8") as stream:
                    manifest = json.loads(next(stream))
                    if not isinstance(manifest, dict) or manifest.get("type") != "manifest":
                        raise ValueError("missing recording manifest")
                    scenario = Scenario.model_validate(manifest["scenario"])
                    result = RunResult.model_validate(manifest["result"])

                    def samples():
                        for line in stream:
                            item = json.loads(line)
                            if not isinstance(item, dict) or item.get("type") != "sample":
                                raise ValueError("invalid recording entry")
                            yield Sample.model_validate(item["data"])

                    verify_recording(scenario, result, samples())
                print(canonical({"verified": True, "passed": result.passed}))
                return 0 if result.passed else 1
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
    except (
        OSError,
        ValueError,
        ValidationError,
        ImportError,
        RuntimeError,
        KeyError,
        StopIteration,
    ) as exc:
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
