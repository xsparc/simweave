"""CLI boundary for pure statistics and local approval history."""

import json
from pathlib import Path

from simweave.contracts import canonical
from simweave.statistics import DecisionPolicy


def register(commands):
    commands.add_parser("statistics-schema", help="print the versioned decision policy schema")
    stats = commands.add_parser("statistics", help="analyze paired seeds from a verified bundle")
    stats.add_argument("path", type=Path)
    stats.add_argument("--policy", required=True, type=Path)
    stats.add_argument("--output", required=True, type=Path)
    history = commands.add_parser("history", help="manage a local immutable baseline catalog")
    actions = history.add_subparsers(dest="action", required=True)
    for name in ("init", "add", "promote", "rollback", "compare", "show", "export", "restore"):
        command = actions.add_parser(name)
        command.add_argument("--database", required=True, type=Path)
        if name in ("export", "restore"):
            command.add_argument("path", type=Path, help="portable catalog archive")
        if name == "add":
            command.add_argument("path", type=Path)
            command.add_argument("--build", required=True)
            command.add_argument("--role", choices=["baseline", "candidate"], default="candidate")
        if name in ("promote", "compare"):
            command.add_argument("build")
        if name in ("promote", "rollback"):
            command.add_argument("--expected-generation", required=True, type=int)
            command.add_argument("--approved-by", required=True)
            command.add_argument("--reason", required=True)
        if name == "promote":
            command.add_argument("--policy", required=True, type=Path)
        if name == "rollback":
            command.add_argument("--to-generation", required=True, type=int)
        if name == "compare":
            command.add_argument("--generation", type=int, help="pin an earlier approval event")
        if name in ("compare", "show"):
            command.add_argument("--output", required=True, type=Path)


def _policy(path: Path) -> DecisionPolicy:
    with path.open("rb") as stream:
        data = stream.read(65537)
    if len(data) > 65536:
        raise ValueError("policy exceeds 64 KiB")
    return DecisionPolicy.model_validate_json(data)


def dispatch(args) -> int:
    from simweave import history
    from simweave.bundles import read_bundle
    from simweave.decision_reports import write_history, write_statistics
    from simweave.statistics import analyze

    if args.command == "statistics-schema":
        print(json.dumps(DecisionPolicy.model_json_schema(), indent=2))
        return 0
    if args.command == "statistics":
        policy = _policy(args.policy)
        manifest, report = read_bundle(args.path)
        result = analyze(
            report,
            report,
            policy,
            individual_gates=True,
            environments=(manifest.environment, manifest.environment),
        )
        write_statistics(result, args.output)
        print(result.model_dump_json())
        return result.exit_code
    if args.action in ("compare", "show") and args.output.exists():
        raise ValueError("output already exists")
    if args.action == "init":
        history.initialize(args.database)
        print(canonical({"schema_version": 1, "initialized": True}))
    elif args.action in ("export", "restore"):
        from simweave.catalog_archive import export_catalog, restore_catalog

        result = (
            export_catalog(args.database, args.path)
            if args.action == "export"
            else restore_catalog(args.path, args.database)
        )
        print(canonical(result))
    elif args.action == "add":
        build = history.add_build(args.database, args.path, args.build, args.role)
        print(canonical({"build": build.label, "digest": history.digest(build)}))
    elif args.action in ("promote", "rollback"):
        approval = history.Approval(
            expected_generation=args.expected_generation,
            approved_by=args.approved_by,
            reason=args.reason,
        )
        event = history.change_baseline(
            args.database,
            approval,
            build=args.build if args.action == "promote" else None,
            policy=_policy(args.policy) if args.action == "promote" else None,
            restore=args.to_generation if args.action == "rollback" else None,
        )
        print(event.model_dump_json())
    elif args.action == "compare":
        comparison = history.compare_build(args.database, args.build, args.generation)
        write_statistics(comparison.statistics, args.output, comparison.model_dump())
        print(comparison.model_dump_json())
        return comparison.statistics.exit_code
    elif args.action == "show":
        data = history.snapshot(args.database)
        write_history(data, args.output)
        print(
            canonical(
                {"generation": data["generation"], "active_baseline": data["active_baseline"]}
            )
        )
    return 0
