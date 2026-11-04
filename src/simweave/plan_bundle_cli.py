"""CLI boundary for portable, non-executing plan-review bundles."""

import json
from pathlib import Path

from simweave.plan_bundle import (
    MAX_BUNDLE,
    MAX_COMPONENT,
    PlanBundle,
    create_bundle,
    decode_json,
    encode_bundle,
    read_bundle,
)
from simweave.sweep_diff import render_plan_diff, render_plan_diff_csv
from simweave.sweeps import Sweep


def register(commands):
    commands.add_parser("sweep-bundle-schema", help="print the plan-review bundle schema")
    export = commands.add_parser("sweep-bundle", help="retain two plans and their v2 comparison")
    export.add_argument("before", type=Path)
    export.add_argument("after", type=Path)
    export.add_argument("--output", required=True, type=Path)
    verify = commands.add_parser("sweep-bundle-verify", help="verify retained plan-review evidence")
    verify.add_argument("path", type=Path)
    render = commands.add_parser("sweep-bundle-render", help="render a verified retained bundle")
    render.add_argument("path", type=Path)
    render.add_argument("--format", choices=("html", "csv"), default="html")
    render.add_argument("--output", required=True, type=Path)


def bounded_read(path, limit):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("input exceeds byte limit")
    return raw


def dispatch(args):
    if args.command == "sweep-bundle-schema":
        print(json.dumps(PlanBundle.model_json_schema(), indent=2))
        return 0
    if args.command == "sweep-bundle":
        sources = [
            Sweep.model_validate(decode_json(bounded_read(path, MAX_COMPONENT)))
            for path in (args.before, args.after)
        ]
        raw = encode_bundle(create_bundle(*sources))
    else:
        bundle = read_bundle(bounded_read(args.path, MAX_BUNDLE))
        if args.command == "sweep-bundle-verify":
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "verified": True,
                        "interpretation": "local_source_consistency_only",
                    }
                )
            )
            return 0
        output = (
            render_plan_diff(bundle.before, bundle.after, schema_version=2)
            if args.format == "html"
            else render_plan_diff_csv(bundle.before, bundle.after)
        )
        raw = output.encode("utf-8")
        if len(raw) > MAX_COMPONENT:
            raise ValueError("rendered comparison exceeds byte limit")
    with args.output.open("xb") as stream:
        stream.write(raw)
    return 0
