"""Create or restore a 100-build archive; verify byte-identical re-export on any OS."""

import argparse
import json
from pathlib import Path

from simweave import history
from simweave.catalog_archive import export_catalog, restore_catalog
from simweave.statistics import DecisionPolicy
from simweave.suites import Suite, execute_suite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    database = args.output / "catalog.sqlite3"
    archive = args.archive
    if archive is None:
        history.initialize(database)
        for index in range(100):
            suite = Suite.model_validate(
                {
                    "name": "Catalog portability",
                    "scenarios": [
                        {
                            "name": "Cart",
                            "world": {"steps": 20},
                            "gates": [{"metric": "rmse", "threshold": 10.0}],
                        }
                    ],
                    "seeds": [0, 1],
                    "adapters": ["reference"],
                    "baseline": {},
                    "candidate": {"kp": 8.0 + index / 100},
                }
            )
            output = args.output / f"build-{index:03}"
            execute_suite(suite, output)
            history.add_build(database, output / "evidence.zip", f"build-{index:03}")
        policy = DecisionPolicy.model_validate(
            {"metrics": [{"metric": "rmse", "max_increase": 0.02}], "resamples": 1000}
        )
        for index in range(3):
            approval = history.Approval(
                expected_generation=index,
                approved_by="portability-check",
                reason="Synthetic fixture approval",
            )
            if index == 2:
                history.change_baseline(database, approval, restore=1)
            else:
                history.change_baseline(
                    database, approval, build=f"build-{index:03}", policy=policy
                )
        for index in range(100):
            history.compare_build(database, f"build-{index:03}")
        archive = args.output / "catalog.ndjson"
        export_catalog(database, archive)
        database = args.output / "restored.sqlite3"
    expected = restore_catalog(archive, database)
    repeated = args.output / "reexport.ndjson"
    actual = export_catalog(database, repeated)
    assert expected == actual
    assert archive.read_bytes() == repeated.read_bytes()
    assert actual["counts"] == {"builds": 100, "events": 3, "comparisons": 100}
    (args.output / "verification.json").write_text(json.dumps(actual, indent=2), encoding="utf-8")
    print(json.dumps(actual))


if __name__ == "__main__":
    main()
