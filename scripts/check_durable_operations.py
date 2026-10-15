"""Real-process acceptance: 100 jobs, 1,000 bundles, recovery and worker death."""

import argparse
import json
import multiprocessing
import tempfile
import time
from pathlib import Path

from simweave.artifacts import Artifacts, Filesystem, key
from simweave.operations_cli import backend
from simweave.suite_jobs import SuiteJobs, work_once
from simweave.suites import Suite, execute_suite


def contract(seed):
    return Suite.model_validate(
        {
            "name": f"acceptance-{seed}",
            "scenarios": [{"world": {"steps": 20}}],
            "seeds": [seed],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {},
        }
    )


def worker(root, start, results, config):
    jobs = SuiteJobs(root / "jobs.db")
    artifacts = Artifacts(
        root / "artifacts.db", backend(config) if config else Filesystem(root / "objects")
    )
    start.wait(30)
    count = 0
    while work_once(jobs, artifacts):
        count += 1
    results.put(count)


def doomed(root, ready):
    jobs = SuiteJobs(root / "jobs.db")
    jobs.lease_seconds = 1
    claim = jobs.claim()
    ready.put({"id": claim["id"], "claim": claim["claim"]})
    time.sleep(60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--s3-config", type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    tempfile.tempdir = str(root)
    started = time.monotonic()
    jobs = SuiteJobs(root / "jobs.db")
    remote = backend(args.s3_config) if args.s3_config else None
    artifacts = Artifacts(root / "artifacts.db", remote or Filesystem(root / "objects"))
    items = [
        (f"tenant-{i % 2}", jobs.submit(f"tenant-{i % 2}", contract(i), f"job-{i}"))
        for i in range(100)
    ]
    context = multiprocessing.get_context("spawn")
    start, results = context.Event(), context.Queue()
    processes = [
        context.Process(target=worker, args=(root, start, results, args.s3_config))
        for _ in range(4)
    ]
    for process in processes:
        process.start()
    start.set()
    try:
        counts = [results.get(timeout=120) for _ in processes]
        for process in processes:
            process.join(10)
            assert process.exitcode == 0
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(10)
    assert sum(counts) == 100 and all(counts)
    for tenant, item in items:
        job = jobs.get(tenant, item["id"])
        assert job["status"] == "succeeded" and job["attempt"] == 1 and job["artifact"]
        assert jobs.get("unrelated", item["id"]) is None

    cancelled = jobs.submit("tenant-0", contract(101), "cancel")
    jobs.cancel("tenant-0", cancelled["id"])
    assert not work_once(jobs, artifacts)
    lost = jobs.submit("tenant-0", contract(102), "lost")
    ready = context.Queue()
    process = context.Process(target=doomed, args=(root, ready))
    process.start()
    claim = ready.get(timeout=30)
    process.terminate()
    process.join(10)
    time.sleep(1.1)
    assert jobs.expire() == 1
    assert jobs.get("tenant-0", lost["id"])["error"] == "worker_lost"
    assert not work_once(jobs, artifacts)
    jobs.retry("tenant-0", lost["id"])
    assert work_once(jobs, artifacts)
    assert jobs.get("tenant-0", lost["id"])["attempt"] == 2
    assert not jobs.finish(lost["id"], claim["claim"], "0" * 64, 0)

    # 1,000 distinct real bundles, not repeated references to one ZIP.
    retained = Artifacts(root / "retained.db", remote or Filesystem(root / "retained"))
    for seed in range(1000):
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            output = Path(temporary) / "suite"
            execute_suite(contract(seed), output)
            digest = retained.put("retention", output / "evidence.zip")
            if seed == 0:
                assert retained.put("retention", output / "evidence.zip") == digest
                if remote:
                    name = key("retention", digest)
                    remote.client.put_object(Bucket=remote.bucket, Key=name, Body=b"corrupt")
                    try:
                        retained.put("retention", output / "evidence.zip")
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("conditional write overwrote a corrupt object")
                    try:
                        retained.get("retention", digest, Path(temporary) / "bad.zip")
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("corrupt object was returned")
                    # Operator repair only, confined to this synthetic test bucket.
                    remote.client.put_object(
                        Bucket=remote.bucket, Key=name, Body=(output / "evidence.zip").read_bytes()
                    )
    recovered = Filesystem(root / "recovered")
    assert retained.recover("retention", recovered) == 1000
    retained.backup(root / "recovered.db")
    restored = Artifacts(root / "recovered.db", recovered)
    with restored.db.connect() as db:
        digests = [row[0] for row in db.execute("SELECT digest FROM artifacts")]
    assert len(set(digests)) == 1000
    for digest in digests:
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            restored.get("retention", digest, Path(temporary) / "check.zip")
    result = {
        "schema_version": 1,
        "jobs": 100,
        "tenants": 2,
        "worker_counts": counts,
        "worker_killed": True,
        "explicit_retry": True,
        "stale_completion_rejected": True,
        "cancelled_job_not_executed": True,
        "retained_and_recovered": 1000,
        "backend": "s3" if remote else "filesystem",
        "seconds": round(time.monotonic() - started, 3),
    }
    (root / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
