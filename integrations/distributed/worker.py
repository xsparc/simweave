"""Four private-scratch workers in one isolated container host for the acceptance drill."""

import json
import multiprocessing
import os
import time
import uuid
from pathlib import Path

from simweave.postgres import Database, Jobs, SharedArtifacts
from simweave.storage_config import backend
from simweave.suite_jobs import work_once


def worker(index):
    database = Database(Path("/tmp") / str(index))
    jobs = Jobs(database)
    artifacts = SharedArtifacts(database, backend(Path("/fixture/storage.json")))
    identifier = os.environ["FIXTURE_HOST"] + "-" + uuid.uuid4().hex
    claims = []
    claim = jobs.claim

    def timed_claim(*args):
        start = time.perf_counter()
        item = claim(*args)
        if item:
            claims.append((time.perf_counter() - start) * 1000)
        return item

    jobs.claim = timed_claim
    if os.environ.get("FIXTURE_HOLD") == "true":
        put = artifacts.put

        def delayed(*args):
            time.sleep(60)
            return put(*args)

        artifacts.put = delayed
    deadline = time.monotonic() + 600
    idle = None
    try:
        while time.monotonic() < deadline:
            if work_once(jobs, artifacts, identifier):
                idle = None
            else:
                active = jobs.metrics(artifacts)["metrics"]
                if active["simweave_suite_jobs_queued"] or active["simweave_suite_jobs_running"]:
                    idle = None
                elif idle is None:
                    idle = time.monotonic()
                elif time.monotonic() - idle > 5:
                    return {"claims": len(claims), "claim_ms": claims}
                time.sleep(0.1)
        raise RuntimeError("fixture deadline exceeded")
    finally:
        jobs.worker_ping(identifier, "offline")
        database.close()


if __name__ == "__main__":
    with multiprocessing.Pool(4) as pool:
        rows = pool.map(worker, range(4))
    Path("/tmp/verification.json").write_text(json.dumps(rows))
