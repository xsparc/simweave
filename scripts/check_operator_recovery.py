"""Physical retained-byte recovery drill; ZIP timestamps distinguish valid fixtures."""

import argparse
import json
import math
import shutil
import tempfile
import zipfile
from pathlib import Path

from simweave import maintenance, recovery
from simweave.artifacts import Artifacts, Filesystem, key
from simweave.bundles import read_bundle
from simweave.suite_jobs import SuiteJobs
from simweave.suites import Suite, execute_suite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gib", type=float, default=10)
    args = parser.parse_args()
    if not 0 < args.gib <= 10:
        raise ValueError("fixture size must be in (0,10] GiB")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    if shutil.disk_usage(root).free < args.gib * 2**30 * 3.5:
        raise ValueError("insufficient space for source, checkpoint and restore")
    tempfile.tempdir = str(root)
    jobs = SuiteJobs(root / "source/queue")
    artifacts = Artifacts(root / "source/index", Filesystem(root / "source/objects"))
    suite = Suite.model_validate(
        {
            "name": "recovery-volume",
            "scenarios": [
                {"world": {"steps": 20000}, "gates": [{"metric": "rmse", "threshold": 10.0}]}
            ],
            "seeds": [1, 2, 3, 4, 5],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {},
        }
    )
    execute_suite(suite, root / "template")
    with zipfile.ZipFile(root / "template/evidence.zip") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    base = root / "fixture.zip"
    with zipfile.ZipFile(base, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    read_bundle(base)  # Semantic recording verification once; only ZIP dates vary below.
    count = math.ceil(args.gib * 2**30 / base.stat().st_size)
    retained = 0
    for index in range(count):
        with zipfile.ZipFile(base, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in members.items():
                info = zipfile.ZipInfo(
                    name, (1980 + index // 336, 1 + (index // 28) % 12, 1 + index % 28, 0, 0, 0)
                )
                archive.writestr(info, data)
        digest = recovery.sha(base)
        tenant = "alpha" if index % 2 else "beta"
        artifacts.backend.put(key(tenant, digest), base)
        size = base.stat().st_size
        with artifacts.db.connect() as db:
            db.execute("INSERT INTO artifacts VALUES(?,?,?)", (tenant, digest, size))
        # Synthetic terminal queue references exercise every retained object.
        job = jobs.submit(tenant, suite, f"fixture-{index}")
        claim = jobs.claim()
        assert claim["id"] == job["id"]
        assert jobs.finish(job["id"], claim["claim"], digest, 0)
        retained += size
        if index % 50 == 0:
            print(json.dumps({"stage": "fixture", "objects": index + 1}), flush=True)
    del members
    base.unlink()
    jobs.gate.set(True)  # Interruption point 1: persisted pause, new operator instance.
    jobs = SuiteJobs(jobs.db.path)
    assert jobs.gate.paused() and jobs.claim() is None
    original = artifacts.backend.get

    def interrupted(*args):
        original(*args)
        raise OSError("synthetic copy interruption")

    artifacts.backend.get = interrupted
    try:
        maintenance.checkpoint(jobs, artifacts, root / "catalogs", root / "checkpoint")
        raise AssertionError("interruption did not fire")
    except OSError:
        assert jobs.gate.paused() and not (root / "checkpoint").exists()
    artifacts.backend.get = original
    print(json.dumps({"stage": "checkpoint", "retained_bytes": retained}), flush=True)
    saved = maintenance.checkpoint(jobs, artifacts, root / "catalogs", root / "checkpoint")
    # Interruption point 3: publication completed but operator exited before resume.
    assert SuiteJobs(jobs.db.path).gate.paused()
    print(json.dumps({"stage": "restore", "checkpoint_seconds": saved["seconds"]}), flush=True)
    restored = recovery.restore(root / "checkpoint", root / "restored")
    recovered = SuiteJobs(root / "restored/runs.sqlite3.suites")
    assert recovered.gate.paused()
    assert saved["references"] == restored["references"] == count
    for tenant in ("alpha", "beta"):
        after = ""
        while items := jobs.list(tenant, after, 100):
            for item in items:
                assert recovered.get(tenant, item["id"]) == item
                path = root / "restored/runs.sqlite3.suites.objects" / key(tenant, item["artifact"])
                assert recovery.sha(path) == item["artifact"]
            after = items[-1]["id"]
    recovered.gate.set(False)
    assert recovered.submit("alpha", suite, "resume")["status"] == "queued"
    result = {
        "schema_version": 1,
        "retained_bytes": retained,
        "objects": count,
        "references": count,
        "interruption_points": 3,
        "missing_references": 0,
        "checkpoint_seconds": saved["seconds"],
        "restore_seconds": restored["seconds"],
        "fixture": (
            "ZIP_STORED verified recordings, distinct ZIP dates, "
            "physical copies; synthetic terminal jobs"
        ),
    }
    (root / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
