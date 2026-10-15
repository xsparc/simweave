"""Run-authority API for durable suites; no client-selected paths or backends."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query

from simweave.suite_jobs import SuiteJobs
from simweave.suites import Suite


def install(app, database, tenant):
    jobs = SuiteJobs(database)
    app.state.suite_jobs = jobs
    Tenant = Annotated[str, Depends(tenant)]

    def required(result):
        if result is None:
            raise HTTPException(404, "suite job not found")
        return result

    @app.post("/api/v1/suite-jobs", status_code=202, tags=["suites"])
    def submit(
        suite: Suite,
        name: Tenant,
        idempotency_key: Annotated[str, Header(pattern=r"^[A-Za-z0-9_-]{1,128}$")],
    ):
        return jobs.submit(name, suite, idempotency_key)

    @app.get("/api/v1/suite-jobs", tags=["suites"])
    def listing(name: Tenant, after: str = "", limit: int = Query(50, ge=1, le=100)):
        return {"schema_version": 1, "items": jobs.list(name, after, limit)}

    @app.get("/api/v1/suite-jobs/{identifier}", tags=["suites"])
    def show(identifier: str, name: Tenant):
        return required(jobs.get(name, identifier))

    @app.post("/api/v1/suite-jobs/{identifier}/cancel", tags=["suites"])
    def cancel(identifier: str, name: Tenant):
        return required(jobs.cancel(name, identifier))

    @app.post("/api/v1/suite-jobs/{identifier}/retry", tags=["suites"])
    def retry(identifier: str, name: Tenant):
        return required(jobs.retry(name, identifier))
