"""Versioned HTTP boundary; heavy simulation belongs to independent workers."""

import importlib.util
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from simweave.config import Settings
from simweave.contracts import (
    RunResult,
    RunsPage,
    RunView,
    Sample,
    Scenario,
    TelemetryPage,
    canonical,
)
from simweave.engine import verify_recording
from simweave.store import Capacity, Conflict, Store


class BodyLimit:
    """Bound chunked as well as Content-Length bodies before validation."""

    def __init__(self, app, maximum=65_536):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.maximum:
                return await JSONResponse({"detail": "request body too large"}, 413)(
                    scope, receive, send
                )
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = Store(settings.database)
    app = FastAPI(title="SimWeave", version="0.1.0", docs_url="/docs", redoc_url=None)
    app.state.store = store
    app.add_middleware(BodyLimit)
    bearer = HTTPBearer(auto_error=False)

    def tenant(auth: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str:
        if auth and auth.scheme.lower() == "bearer" and auth.credentials.isascii():
            for token, name in settings.tokens.items():
                if secrets.compare_digest(auth.credentials, token):
                    return name
        raise HTTPException(
            401, "valid bearer token required", headers={"WWW-Authenticate": "Bearer"}
        )

    Tenant = Annotated[str, Depends(tenant)]

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": error["loc"], "type": error["type"], "msg": error["msg"]}
                    for error in exc.errors()
                ]
            },
        )

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(Capacity)
    async def capacity(request, exc):
        return JSONResponse(
            status_code=429, content={"detail": str(exc)}, headers={"Retry-After": "5"}
        )

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    def required(name, identifier):
        run = store.get(name, identifier)
        if not run:
            raise HTTPException(404, "run not found")
        return run

    @app.get("/healthz", tags=["operations"])
    def health():
        return {"status": "ok"}

    @app.get("/api/v1/capabilities", tags=["contracts"])
    def capabilities(name: Tenant):
        return {
            "schema_versions": [1],
            "adapters": [
                {"id": "reference", "available": True, "kind": "experiment"},
                {
                    "id": "mujoco",
                    "available": importlib.util.find_spec("mujoco") is not None,
                    "kind": "experiment",
                },
                {"id": "ros2", "available": False, "kind": "operator_lifecycle_bridge"},
            ],
            "max_steps": 20_000,
            "max_active_runs_per_tenant": 20,
        }

    @app.get("/api/v1/scenario-schema", tags=["contracts"])
    def scenario_schema(name: Tenant):
        return Scenario.model_json_schema()

    @app.post("/api/v1/runs", status_code=202, response_model=RunView, tags=["runs"])
    def submit(
        scenario: Scenario,
        response: Response,
        name: Tenant,
        idempotency_key: Annotated[
            str | None, Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
        ] = None,
    ):
        if scenario.adapter == "mujoco" and importlib.util.find_spec("mujoco") is None:
            raise HTTPException(422, "MuJoCo is not installed in the service environment")
        run, created = store.submit(name, scenario, idempotency_key)
        response.status_code = 202 if created else 200
        response.headers["Location"] = f"/api/v1/runs/{run['id']}"
        return run

    @app.get("/api/v1/runs", response_model=RunsPage, tags=["runs"])
    def runs(
        name: Tenant,
        limit: Annotated[int, Query(ge=1, le=100)] = 30,
        before: Annotated[str | None, Query(max_length=32)] = None,
    ):
        try:
            items = store.list(name, limit, before)
        except ValueError:
            raise HTTPException(400, "invalid pagination cursor") from None
        return {"items": items, "next_before": items[-1]["id"] if len(items) == limit else None}

    @app.get("/api/v1/runs/{identifier}", response_model=RunView, tags=["runs"])
    def get_run(identifier: str, name: Tenant):
        return required(name, identifier)

    @app.post("/api/v1/runs/{identifier}/cancel", response_model=RunView, tags=["runs"])
    def cancel(identifier: str, name: Tenant):
        run = store.cancel(name, identifier)
        if not run:
            raise HTTPException(404, "run not found")
        return run

    @app.delete("/api/v1/runs/{identifier}", status_code=204, tags=["runs"])
    def delete(identifier: str, name: Tenant):
        if not store.delete(name, identifier):
            raise HTTPException(404, "run not found")
        return Response(status_code=204)

    @app.get(
        "/api/v1/runs/{identifier}/telemetry", response_model=TelemetryPage, tags=["recordings"]
    )
    def telemetry(
        identifier: str,
        name: Tenant,
        after: Annotated[int, Query(ge=-1)] = -1,
        limit: Annotated[int, Query(ge=1, le=1000)] = 1000,
    ):
        required(name, identifier)
        items = store.samples(name, identifier, after, limit)
        return {"items": items, "next_after": items[-1]["step"] if len(items) == limit else None}

    @app.post("/api/v1/runs/{identifier}/verify", tags=["recordings"])
    def verify(identifier: str, name: Tenant):
        run = required(name, identifier)
        if run["status"] != "succeeded":
            raise HTTPException(409, "only completed recordings can be verified")
        try:
            verify_recording(
                Scenario.model_validate(run["scenario"]),
                RunResult.model_validate(run["result"]),
                (Sample.model_validate(s) for s in store.iter_samples(name, identifier)),
            )
        except ValueError:
            raise HTTPException(409, "recording integrity check failed") from None
        return {"verified": True, "passed": run["result"]["passed"]}

    @app.get("/api/v1/runs/{identifier}/recording", tags=["recordings"])
    def recording(identifier: str, name: Tenant):
        run = required(name, identifier)
        if run["status"] != "succeeded":
            raise HTTPException(409, "recording not completed")

        def lines():
            yield (
                canonical(
                    {"type": "manifest", "scenario": run["scenario"], "result": run["result"]}
                )
                + "\n"
            )
            for sample in store.iter_samples(name, identifier):
                yield canonical({"type": "sample", "data": sample}) + "\n"

        return StreamingResponse(
            lines(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{identifier}.jsonl"'},
        )

    return app
