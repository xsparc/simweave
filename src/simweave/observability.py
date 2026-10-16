"""Fixed-cardinality durable counters and operational snapshots."""

import time
from functools import wraps


def counted(operation):
    def decorate(function):
        @wraps(function)
        def invoke(self, *args, **kwargs):
            suffix = "failures_total"
            try:
                result = function(self, *args, **kwargs)
                suffix = "successes_total"
                return result
            finally:
                self.count_operation(operation + "_" + suffix)

        return invoke

    return decorate


def snapshot(jobs, artifacts, tenant=None):
    if hasattr(jobs, "metrics"):
        return jobs.metrics(artifacts, tenant)
    now = time.time()
    where, args = ("WHERE tenant=?", (tenant,)) if tenant else ("", ())
    with jobs.db.connect() as db:
        rows = db.execute(
            f"SELECT status,count(*) FROM suite_jobs_v1 {where} GROUP BY status", args
        )
        counts = dict(rows)
        conjunction = "AND" if tenant else "WHERE"
        oldest = db.execute(
            f"SELECT min(created) FROM suite_jobs_v1 {where} {conjunction} status='queued'", args
        ).fetchone()[0]
        lost = db.execute(
            f"SELECT count(*) FROM suite_jobs_v1 {where} {conjunction} error='worker_lost'", args
        ).fetchone()[0]
        healthy = db.execute(
            "SELECT count(*) FROM suite_workers WHERE updated>? AND state!='offline'", (now - 30,)
        ).fetchone()[0]
        losses = db.execute("SELECT value FROM suite_counters WHERE name='lease_losses'").fetchone()
    result = {
        f"simweave_suite_jobs_{state}": counts.get(state, 0)
        for state in ("queued", "running", "succeeded", "failed", "cancelled")
    }
    result["simweave_suite_queue_oldest_seconds"] = max(0, now - oldest) if oldest else 0
    result["simweave_suite_worker_lost_jobs"] = lost
    if tenant is None:
        result["simweave_suite_lease_losses_total"] = losses[0] if losses else 0
        result["simweave_workers_fresh"] = healthy
        with artifacts.db.connect() as db:
            counters = dict(db.execute("SELECT name,value FROM operation_counters"))
            result["simweave_artifacts_retained"] = db.execute(
                "SELECT count(*) FROM artifacts"
            ).fetchone()[0]
        for operation in ("artifact_put", "artifact_get"):
            for outcome in ("successes_total", "failures_total"):
                name = operation + "_" + outcome
                result["simweave_" + name] = counters.get(name, 0)
    return {"schema_version": 1, "metrics": result}


def prometheus(value):
    lines = []
    for name, number in sorted(value["metrics"].items()):
        kind = "counter" if name.endswith("_total") else "gauge"
        lines.extend((f"# TYPE {name} {kind}", f"{name} {number}"))
    return "\n".join(lines) + "\n"
