"""CLI boundary for portable, non-executing plan-review bundles."""

import json
from pathlib import Path

from simweave.bundle_identity import (
    MAX_IDENTITY_BYTES,
    BundleIdentity,
    bundle_identity,
    read_bundle_identity,
    verify_bundle_identity,
    verify_bundle_identity_record,
)
from simweave.plan_bundle import (
    MAX_BUNDLE,
    MAX_COMPONENT,
    PlanBundle,
    create_bundle,
    decode_json,
    encode_bundle,
    read_bundle,
    verify_bundle_csv,
    verify_bundle_html,
    verify_bundle_sources,
)
from simweave.sweep_diff import render_plan_diff, render_plan_diff_csv
from simweave.sweeps import Sweep


def register(commands):
    commands.add_parser("sweep-bundle-identity-schema", help="print the retained identity schema")
    commands.add_parser("sweep-bundle-schema", help="print the plan-review bundle schema")
    export = commands.add_parser("sweep-bundle", help="retain two plans and their v2 comparison")
    export.add_argument("before", type=Path)
    export.add_argument("after", type=Path)
    export.add_argument("--output", required=True, type=Path)
    verify = commands.add_parser("sweep-bundle-verify", help="verify retained plan-review evidence")
    verify.add_argument("path", type=Path)
    sources = commands.add_parser(
        "sweep-bundle-verify-sources", help="verify a bundle against explicit sources"
    )
    sources.add_argument("path", type=Path)
    sources.add_argument("before", type=Path)
    sources.add_argument("after", type=Path)
    csv_check = commands.add_parser(
        "sweep-bundle-verify-csv", help="verify canonical CSV against a bundle"
    )
    csv_check.add_argument("path", type=Path)
    csv_check.add_argument("csv", type=Path)
    html_check = commands.add_parser("sweep-bundle-verify-html", help="verify exact retained HTML")
    html_check.add_argument("path", type=Path)
    html_check.add_argument("html", type=Path)
    html_check.add_argument("--before", type=Path)
    html_check.add_argument("--after", type=Path)
    identity = commands.add_parser("sweep-bundle-identity", help="print normalized bundle identity")
    identity.add_argument("path", type=Path)
    render = commands.add_parser("sweep-bundle-render", help="render a verified retained bundle")
    render.add_argument("path", type=Path)
    render.add_argument("--format", choices=("html", "csv"), default="html")
    render.add_argument("--output", required=True, type=Path)
    render.add_argument("--before", type=Path)
    render.add_argument("--after", type=Path)
    for command in (export, verify, sources, csv_check, html_check, render):
        expected = command.add_mutually_exclusive_group()
        expected.add_argument("--expected-sha256")
        expected.add_argument("--identity", type=Path)


def bounded_read(path, limit):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("input exceeds byte limit")
    return raw


def check_identity(args, bundle):
    if getattr(args, "identity", None) is not None:
        verify_bundle_identity_record(
            bundle, read_bundle_identity(bounded_read(args.identity, MAX_IDENTITY_BYTES))
        )
    if getattr(args, "expected_sha256", None) is not None:
        verify_bundle_identity(bundle, args.expected_sha256)


def dispatch(args):
    if args.command == "sweep-bundle-identity-schema":
        print(json.dumps(BundleIdentity.model_json_schema(), indent=2))
        return 0
    if args.command == "sweep-bundle-schema":
        print(json.dumps(PlanBundle.model_json_schema(), indent=2))
        return 0
    if args.command == "sweep-bundle":
        sources = [
            Sweep.model_validate(decode_json(bounded_read(path, MAX_COMPONENT)))
            for path in (args.before, args.after)
        ]
        bundle = create_bundle(*sources)
        check_identity(args, bundle)
        raw = encode_bundle(bundle)
    else:
        retained = bounded_read(args.path, MAX_BUNDLE)
        bundle = read_bundle(retained)
        check_identity(args, bundle)
        if args.command == "sweep-bundle-identity":
            print(json.dumps(bundle_identity(bundle)))
            return 0
        if args.command in {"sweep-bundle-render", "sweep-bundle-verify-html"}:
            if (args.before is None) != (args.after is None):
                raise ValueError("both source plans are required")
            if args.before is not None:
                sources = [
                    Sweep.model_validate(decode_json(bounded_read(path, MAX_COMPONENT)))
                    for path in (args.before, args.after)
                ]
                verify_bundle_sources(retained, *sources)
        if args.command == "sweep-bundle-verify-sources":
            sources = [
                Sweep.model_validate(decode_json(bounded_read(path, MAX_COMPONENT)))
                for path in (args.before, args.after)
            ]
            verify_bundle_sources(retained, *sources)
        elif args.command == "sweep-bundle-verify-csv":
            verify_bundle_csv(bundle, bounded_read(args.csv, MAX_COMPONENT))
        elif args.command == "sweep-bundle-verify-html":
            verify_bundle_html(bundle, bounded_read(args.html, MAX_COMPONENT))
        if args.command in {
            "sweep-bundle-verify-html",
            "sweep-bundle-verify",
            "sweep-bundle-verify-sources",
            "sweep-bundle-verify-csv",
        }:
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
