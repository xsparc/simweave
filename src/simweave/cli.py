"""Portable CLI with machine-readable outputs and useful exit codes."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from simweave.contracts import RunResult, Sample, Scenario, canonical
from simweave.engine import execute, verify_recording
from simweave.store import Capacity, Conflict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="simweave")
    commands = parser.add_subparsers(dest="command", required=True)
    from simweave.attestation import dispatch as attestation_dispatch
    from simweave.attestation import register as attestation_register
    from simweave.decision_cli import dispatch, register
    from simweave.operations_cli import dispatch as operations_dispatch
    from simweave.operations_cli import register as operations_register

    register(commands)
    attestation_register(commands)
    operations_register(commands)
    init = commands.add_parser("init", help="write an example scenario")
    init.add_argument("path", type=Path)
    commands.add_parser("schema", help="print the scenario JSON Schema")
    commands.add_parser("suite-schema", help="print the regression suite JSON Schema")
    commands.add_parser("sweep-schema", help="print the parameter sweep JSON Schema")
    sweep = commands.add_parser("sweep", help="plan a bounded parameter sweep without execution")
    sweep.add_argument("path", type=Path)
    sweep.add_argument("--output", type=Path, help="write a new Suite JSON file; default stdout")
    inspect = commands.add_parser("sweep-inspect", help="preview admitted run and step counts")
    inspect.add_argument("path", type=Path)
    inspect.add_argument("--output", type=Path, help="write new workload JSON; default stdout")
    commands.add_parser("sweep-inspect-schema", help="print the sweep workload JSON Schema")
    commands.add_parser("sweep-review-schema", help="print the sweep review JSON Schema")
    sweep_review = commands.add_parser("sweep-review", help="summarize results by sweep point")
    sweep_review.add_argument("sweep", type=Path)
    sweep_review.add_argument("report", type=Path)
    sweep_review.add_argument("--output", type=Path, help="write a new review file; default stdout")
    sweep_review.add_argument("--format", choices=["json", "html", "csv"], default="json")
    suite = commands.add_parser("suite", help="run a bounded baseline/candidate regression matrix")
    suite.add_argument("path", type=Path)
    suite.add_argument("--output", required=True, type=Path)
    suite.add_argument("--source-revision", help="explicit 40-character Git commit (provenance)")
    suite.add_argument("--image-id", help="explicit local sha256 Docker image ID (provenance)")
    report = commands.add_parser("report", help="convert a suite JSON report to standalone HTML")
    report.add_argument("path", type=Path)
    report.add_argument("--output", required=True, type=Path)
    bundle_check = commands.add_parser("bundle-check", help="verify bundle metadata and recordings")
    bundle_check.add_argument("path", type=Path)
    for name, help_text in (
        ("rerun", "rerun a bundle in an explicitly selected local container image"),
        ("_bundle-rerun", argparse.SUPPRESS),
    ):
        rerun = commands.add_parser(name, help=help_text)
        rerun.add_argument("path", type=Path)
        rerun.add_argument("--output", required=True, type=Path)
        if name == "rerun":
            rerun.add_argument("--image", required=True, help="trusted local sha256 image ID")
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
        if args.command in ("sweep-review", "sweep-review-schema"):
            from simweave.bundles import MAX_REPORT
            from simweave.suites import SuiteReport
            from simweave.sweep_review import SweepReview, summarize
            from simweave.sweeps import Sweep

            if args.command == "sweep-review-schema":
                print(json.dumps(SweepReview.model_json_schema(), indent=2))
                return 0
            with args.sweep.open("rb") as stream:
                sweep_bytes = stream.read(65_537)
            with args.report.open("rb") as stream:
                report_bytes = stream.read(MAX_REPORT + 1)
            if len(sweep_bytes) > 65_536 or len(report_bytes) > MAX_REPORT:
                raise ValueError("review input exceeds its byte limit")
            source = Sweep.model_validate_json(sweep_bytes)
            report = SuiteReport.model_validate_json(report_bytes)
            if args.format == "html":
                from simweave.sweep_html import render_sweep_report

                output, exit_code = render_sweep_report(source, report)
            elif args.format == "csv":
                from simweave.sweep_csv import render_sweep_csv

                output, exit_code = render_sweep_csv(source, report)
            else:
                result = summarize(source, report)
                output, exit_code = result.model_dump_json(indent=2) + "\n", result.exit_code
            if args.output is None:
                if args.format == "csv" and hasattr(sys.stdout, "buffer"):
                    # Preserve UTF-8 and CRLF even with Windows text-stream translation.
                    sys.stdout.buffer.write(output.encode("utf-8"))
                else:
                    print(output, end="")
            else:
                with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(output)
            return exit_code
        if args.command in ("sweep", "sweep-schema", "sweep-inspect", "sweep-inspect-schema"):
            from simweave.sweep_inspect import SweepWorkload, inspect_sweep
            from simweave.sweeps import Sweep, plan

            if args.command == "sweep-schema":
                print(json.dumps(Sweep.model_json_schema(), indent=2))
                return 0
            if args.command == "sweep-inspect-schema":
                print(json.dumps(SweepWorkload.model_json_schema(), indent=2))
                return 0
            with args.path.open("rb") as stream:
                raw = stream.read(65_537)
            if len(raw) > 65_536:
                raise ValueError("sweep input exceeds 64 KiB")
            source = Sweep.model_validate_json(raw)
            contract = inspect_sweep(source) if args.command == "sweep-inspect" else plan(source)
            output = contract.model_dump_json() + "\n"
            if len(output.encode("utf-8")) > 65_536:
                raise ValueError("generated suite exceeds 64 KiB")
            if args.output is None:
                print(output, end="")
            else:
                with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(output)
            return 0
        if args.command == "operations":
            return operations_dispatch(args)
        if args.command == "attestation":
            return attestation_dispatch(args)
        if args.command in ("statistics", "statistics-schema", "history", "calibrate"):
            return dispatch(args)
        if args.command == "report":
            from simweave.bundles import MAX_REPORT
            from simweave.offline import write_report
            from simweave.suites import SuiteReport

            if args.path.stat().st_size > MAX_REPORT:
                raise ValueError("report exceeds 4 MiB")
            write_report(SuiteReport.model_validate_json(args.path.read_bytes()), args.output)
            print(canonical({"report_written": True, "provenance": "unknown"}))
            return 0
        if args.command == "bundle-check":
            from simweave.bundles import read_bundle

            manifest, report = read_bundle(args.path)
            print(
                canonical(
                    {
                        "verified": True,
                        "suite_digest": report.suite_digest,
                        "recordings": sum(c.summary is not None for c in report.cases),
                        "execution_errors": sum(c.error is not None for c in report.cases),
                        "environment": manifest.environment.model_dump(),
                    }
                )
            )
            return 0
        if args.command in ("rerun", "_bundle-rerun"):
            from simweave.rerun import rerun_container, rerun_here

            code = (
                rerun_container(args.path, args.image, args.output)
                if args.command == "rerun"
                else rerun_here(args.path, args.output)
            )
            print((args.output / "reproduction.json").read_text(encoding="utf-8"))
            return code
        if args.command in ("suite", "suite-schema"):
            from simweave.provenance import capture
            from simweave.suites import Suite, execute_suite, review

            if args.command == "suite-schema":
                print(json.dumps(Suite.model_json_schema(), indent=2))
                return 0
            if args.path.stat().st_size > 65_536:
                raise ValueError("suite input exceeds 64 KiB")
            contract = Suite.model_validate_json(args.path.read_bytes())
            report = execute_suite(
                contract,
                args.output,
                environment=capture(args.source_revision, args.image_id),
            )
            result = review(report)
            print(
                canonical(
                    {
                        "name": result.name,
                        "suite_digest": result.suite_digest,
                        "runs": len(report.cases),
                        "pairs": len(result.pairs),
                        "exit_code": result.exit_code,
                    }
                )
            )
            return result.exit_code
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
        Capacity,
        Conflict,
        sqlite3.Error,
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
