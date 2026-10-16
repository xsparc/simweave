"""Four independent worker processes drain without starting queued follow-up work."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from check_connected_operations import contract

from simweave import maintenance
from simweave.artifacts import Artifacts, Filesystem
from simweave.store import Conflict
from simweave.suite_jobs import SuiteJobs, work_once


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", type=int)
    args = parser.parse_args()
    root = args.output.resolve()
    if args.worker is None:
        root.mkdir(parents=True, exist_ok=False)
    jobs = SuiteJobs(root / "queue")
    artifacts = Artifacts(root / "index", Filesystem(root / "objects"))
    if args.worker is not None:
        original = artifacts.put

        def put(*values):
            (root / f"ready-{args.worker}").touch()
            deadline = time.monotonic() + 40
            while not (root / "release").exists():
                if time.monotonic() > deadline:
                    raise RuntimeError("worker fixture barrier timed out")
                time.sleep(0.05)
            return original(*values)

        artifacts.put = put
        assert work_once(jobs, artifacts, f"process-{args.worker}")
        assert not work_once(jobs, artifacts, f"process-{args.worker}")
        return
    for i in range(8):
        jobs.submit("alpha" if i % 2 else "beta", contract(i), str(i))
    workers = []
    try:
        for i in range(4):
            workers.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--output",
                        str(root),
                        "--worker",
                        str(i),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )
        deadline = time.monotonic() + 30
        while len(list(root.glob("ready-*"))) != 4:
            if any(w.poll() is not None for w in workers) or time.monotonic() > deadline:
                raise RuntimeError("worker startup failed")
            time.sleep(0.05)
        jobs.gate.set(True)
        try:
            jobs.submit("alpha", contract(10), "paused")
            raise AssertionError("paused admission accepted work")
        except Conflict:
            pass
        try:
            maintenance.drain(jobs, 0)
            raise AssertionError("busy worker drain accepted")
        except Conflict:
            pass
        (root / "release").touch()
        assert all(w.wait(timeout=30) == 0 for w in workers)
        assert maintenance.drain(jobs, 5)["drained"]
        with jobs.db.connect() as db:
            states = dict(db.execute("SELECT status,count(*) FROM suite_jobs_v1 GROUP BY status"))
        assert states == {"queued": 4, "succeeded": 4}, states
        jobs.gate.set(False)
        assert work_once(jobs, artifacts)
        result = {
            "schema_version": 1,
            "worker_processes": 4,
            "tenants": 2,
            "completed_before_resume": 4,
            "queued_until_resume": 4,
            "resumed": True,
        }
        (root / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.terminate()
                worker.wait(timeout=10)


if __name__ == "__main__":
    main()
