"""Run synthetic portable plan review without executing a simulator."""

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

from simweave.bundle_identity import bundle_identity
from simweave.cli import main
from simweave.plan_bundle import read_bundle


def require(condition):
    if not condition:
        raise RuntimeError("portable review acceptance failed")


def cli(args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return main(list(map(str, args)))


def run(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=False)
    before, after, bundle, identity = [
        directory / n for n in ("before.json", "after.json", "bundle.json", "identity.json")
    ]
    for path, seed in [(before, 1), (after, 2)]:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(
                {
                    "name": "synthetic",
                    "scenario": {"world": {"steps": 10}},
                    "axes": [{"field": "robot.mass", "values": [1.0, 2.0]}],
                    "seeds": [seed],
                    "adapters": ["reference"],
                    "baseline": {},
                    "candidate": {},
                },
                stream,
            )
    with patch("simweave.suites.execute", side_effect=RuntimeError("simulation invoked")):
        require(cli(["sweep-bundle", before, after, "--output", bundle]) == 0)
        record = bundle_identity(read_bundle(bundle.read_bytes()))
        identity.write_text(json.dumps(record), encoding="utf-8")
        saved = {p: p.read_bytes() for p in (before, after, bundle, identity)}
        for format in ("html", "csv"):
            output = directory / ("review." + format)
            args = [
                "sweep-bundle-render",
                bundle,
                "--format",
                format,
                "--before",
                before,
                "--after",
                after,
                "--identity",
                identity,
                "--output",
                output,
            ]
            require(cli(args) == 0)
            raw = output.read_bytes()
            require(cli(args) == 2 and output.read_bytes() == raw)
            require(
                cli(
                    [
                        "sweep-bundle-verify-" + format,
                        bundle,
                        output,
                        "--identity",
                        identity,
                        "--before",
                        before,
                        "--after",
                        after,
                    ]
                )
                == 0
            )
            saved[output] = raw
            tampered = directory / ("tampered." + format)
            tampered.write_bytes(raw + b"\n")
            require(
                cli(
                    [
                        "sweep-bundle-verify-" + format,
                        bundle,
                        tampered,
                        "--identity",
                        identity,
                        "--before",
                        before,
                        "--after",
                        after,
                    ]
                )
                == 2
            )
            require(tampered.read_bytes() == raw + b"\n")
        replacement = directory / "replacement.json"
        require(cli(["sweep-bundle", before, before, "--output", replacement]) == 0)
        replacement_id = directory / "replacement-identity.json"
        replacement_id.write_text(
            json.dumps(bundle_identity(read_bundle(replacement.read_bytes()))), encoding="utf-8"
        )
        require(cli(["sweep-bundle-verify", replacement, "--identity", replacement_id]) == 0)
        for format in ("html", "csv"):
            blocked = directory / ("blocked." + format)
            require(
                cli(
                    [
                        "sweep-bundle-render",
                        replacement,
                        "--format",
                        format,
                        "--before",
                        before,
                        "--after",
                        after,
                        "--identity",
                        replacement_id,
                        "--output",
                        blocked,
                    ]
                )
                == 2
            )
            require(not blocked.exists())
            replaced_output = directory / ("replacement." + format)
            require(
                cli(
                    [
                        "sweep-bundle-render",
                        replacement,
                        "--format",
                        format,
                        "--identity",
                        replacement_id,
                        "--output",
                        replaced_output,
                    ]
                )
                == 0
            )
            verify = [
                "sweep-bundle-verify-" + format,
                replacement,
                replaced_output,
                "--identity",
                replacement_id,
            ]
            require(cli(verify) == 0)
            require(cli(verify + ["--before", before, "--after", after]) == 2)
        require(all(p.read_bytes() == raw for p, raw in saved.items()))
    return {"verified": True, "formats": ["html", "csv"], "simulation": "none"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.directory)))
    except Exception:
        print(json.dumps({"error": "acceptance_failed"}), file=sys.stderr)
        raise SystemExit(2) from None
