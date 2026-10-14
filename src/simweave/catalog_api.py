"""Tenant-scoped catalog routes; no request-controlled database paths or identity."""

import secrets
import sqlite3
import tempfile
from pathlib import Path
from threading import BoundedSemaphore
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import Path as PathParameter
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import Field

from simweave import history
from simweave.bundles import MAX_TOTAL
from simweave.config import CatalogPrincipal, Settings
from simweave.statistics import DecisionPolicy, Role, Versioned


class Promote(Versioned):
    build: history.Label
    policy: DecisionPolicy
    expected_generation: int = Field(ge=0, le=history.MAX_EVENTS)
    reason: str = Field(min_length=1, max_length=500)


class Rollback(Versioned):
    to_generation: int = Field(ge=1, le=history.MAX_EVENTS)
    expected_generation: int = Field(ge=0, le=history.MAX_EVENTS)
    reason: str = Field(min_length=1, max_length=500)


class Compare(Versioned):
    build: history.Label
    generation: int | None = Field(default=None, ge=1, le=history.MAX_EVENTS)


def install(app, settings: Settings):
    root = settings.database.parent / (settings.database.name + ".catalogs")
    catalogs = {}
    for principal in settings.tokens.values():
        if isinstance(principal, CatalogPrincipal) and principal.tenant not in catalogs:
            root.mkdir(parents=True, exist_ok=True)
            # Prefix also makes Windows device names (e.g. tenant "con") safe filenames.
            path = root / ("tenant-" + principal.tenant + ".sqlite3")
            if not path.exists():
                import os

                with tempfile.TemporaryDirectory(dir=root) as folder:
                    temporary = Path(folder) / "catalog.sqlite3"
                    history.initialize(temporary)
                    try:
                        os.link(temporary, path)
                    except FileExistsError:
                        pass  # Another server process provisioned the same tenant.
            with history._connect(path):
                pass
            catalogs[principal.tenant] = path
    router = APIRouter(prefix="/api/v1/catalog", tags=["baseline catalog"])
    bearer = HTTPBearer(auto_error=False)
    slots = BoundedSemaphore(2)

    def principal(auth: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
        if auth and auth.scheme.lower() == "bearer" and auth.credentials.isascii():
            for token, identity in settings.tokens.items():
                if secrets.compare_digest(token, auth.credentials):
                    if isinstance(identity, CatalogPrincipal):
                        return identity
                    raise HTTPException(403, "catalog permission required")
        raise HTTPException(
            401, "valid bearer token required", headers={"WWW-Authenticate": "Bearer"}
        )

    Principal = Annotated[CatalogPrincipal, Depends(principal)]

    def require(identity, role):
        if identity.role != role:
            raise HTTPException(403, f"catalog {role} permission required")

    def call(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except (ValueError, sqlite3.Error, OSError):
            raise HTTPException(
                409, "catalog operation rejected; check evidence, limits and generation"
            ) from None

    def build_exists(path, label):
        with history._connect(path) as connection:
            if not connection.execute("SELECT 1 FROM builds WHERE label=?", (label,)).fetchone():
                raise HTTPException(404, "build not found")

    @router.get("")
    def overview(identity: Principal):
        with history._connect(catalogs[identity.tenant]) as connection:
            generation = connection.execute(
                "SELECT coalesce(max(generation),0) FROM events"
            ).fetchone()[0]
            event = history._event(connection, generation) if generation else None
            return {
                "schema_version": 1,
                "generation": generation,
                "active_baseline": event.build if event else None,
                "role": identity.role,
                "subject": identity.subject,
            }

    @router.get("/builds")
    def builds(
        identity: Principal,
        after: Annotated[int, Query(ge=0, le=history.MAX_BUILDS)] = 0,
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ):
        with history._connect(catalogs[identity.tenant]) as connection:
            rows = connection.execute(
                "SELECT rowid,label,digest FROM builds WHERE rowid>? ORDER BY rowid LIMIT ?",
                (after, limit),
            ).fetchall()
        return {
            "schema_version": 1,
            "items": [{"cursor": r[0], "label": r[1], "digest": r[2]} for r in rows],
            "next_after": rows[-1][0] if len(rows) == limit else None,
        }

    @router.get("/builds/{label}", response_model=history.Build)
    def get_build(label: history.Label, identity: Principal):
        path = catalogs[identity.tenant]
        build_exists(path, label)
        with history._connect(path) as connection:
            return call(history._build, connection, label)

    @router.put(
        "/builds/{label}",
        status_code=201,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
            }
        },
    )
    async def import_build(
        label: history.Label, request: Request, identity: Principal, role: Role = "candidate"
    ):
        require(identity, "importer")
        if request.headers.get("content-type") != "application/zip":
            raise HTTPException(415, "application/zip required")
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "catalog import capacity reached")
        try:
            with tempfile.TemporaryDirectory(prefix="upload-", dir=root) as folder:
                upload = Path(folder) / "evidence.zip"
                size = 0
                with upload.open("xb") as stream:
                    async for chunk in request.stream():
                        size += len(chunk)
                        if size > MAX_TOTAL:
                            raise HTTPException(413, "evidence bundle exceeds limit")
                        stream.write(chunk)
                build = await run_in_threadpool(
                    call, history.add_build, catalogs[identity.tenant], upload, label, role
                )
                return {"schema_version": 1, "build": build.label, "digest": history.digest(build)}
        finally:
            slots.release()

    @router.get("/events")
    def events(
        identity: Principal,
        after: Annotated[int, Query(ge=0, le=history.MAX_EVENTS)] = 0,
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ):
        with history._connect(catalogs[identity.tenant]) as connection:
            rows = connection.execute(
                "SELECT generation FROM events WHERE generation>? ORDER BY generation LIMIT ?",
                (after, limit),
            ).fetchall()
            items = [call(history._event, connection, r[0]).model_dump() for r in rows]
        return {
            "schema_version": 1,
            "items": items,
            "next_after": rows[-1][0] if len(rows) == limit else None,
        }

    @router.post("/promote", response_model=history.BaselineEvent, status_code=201)
    def promote(body: Promote, identity: Principal):
        require(identity, "approver")
        path = catalogs[identity.tenant]
        build_exists(path, body.build)
        approval = call(
            history.Approval,
            expected_generation=body.expected_generation,
            approved_by=identity.subject,
            reason=body.reason,
        )
        return call(history.change_baseline, path, approval, build=body.build, policy=body.policy)

    @router.post("/rollback", response_model=history.BaselineEvent, status_code=201)
    def rollback(body: Rollback, identity: Principal):
        require(identity, "approver")
        approval = call(
            history.Approval,
            expected_generation=body.expected_generation,
            approved_by=identity.subject,
            reason=body.reason,
        )
        return call(
            history.change_baseline, catalogs[identity.tenant], approval, restore=body.to_generation
        )

    @router.post("/comparisons", response_model=history.BuildComparison, status_code=201)
    def compare(body: Compare, identity: Principal):
        require(identity, "importer")
        path = catalogs[identity.tenant]
        build_exists(path, body.build)
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "catalog comparison capacity reached")
        try:
            return call(history.compare_build, path, body.build, body.generation)
        finally:
            slots.release()

    @router.get("/comparisons")
    def comparisons(
        identity: Principal,
        after: Annotated[int, Query(ge=0, le=history.MAX_COMPARISONS)] = 0,
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ):
        with history._connect(catalogs[identity.tenant]) as connection:
            rows = connection.execute(
                "SELECT id,digest FROM comparisons WHERE id>? ORDER BY id LIMIT ?", (after, limit)
            ).fetchall()
        return {
            "schema_version": 1,
            "items": [{"id": r[0], "digest": r[1]} for r in rows],
            "next_after": rows[-1][0] if len(rows) == limit else None,
        }

    @router.get("/comparisons/{identifier}", response_model=history.BuildComparison)
    def comparison(
        identifier: Annotated[int, PathParameter(ge=1, le=history.MAX_COMPARISONS)],
        identity: Principal,
    ):
        with history._connect(catalogs[identity.tenant]) as connection:
            row = connection.execute(
                "SELECT digest,payload FROM comparisons WHERE id=?", (identifier,)
            ).fetchone()
            if row is None:
                raise HTTPException(404, "comparison not found")
            return call(history._decode, row, history.BuildComparison)

    app.include_router(router)
