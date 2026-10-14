"""Local immutable decision catalog. Approval labels are assertions, not identities."""

from __future__ import annotations

import hashlib
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator

from simweave.bundles import MAX_TOTAL, read_bundle
from simweave.contracts import canonical
from simweave.provenance import Digest, Environment
from simweave.statistics import DecisionPolicy, Role, StatisticalReport, Versioned, analyze
from simweave.suites import SuiteReport

Label = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")]
APPLICATION_ID = 0x53574831
MAX_BUILDS = 100
MAX_EVENTS = 1000
MAX_COMPARISONS = 1000
MAX_SNAPSHOT = 4 * 1024 * 1024 + 8192


def digest(value: Versioned) -> str:
    return hashlib.sha256(canonical(value.model_dump()).encode()).hexdigest()


class Build(Versioned):
    label: Label
    role: Role
    bundle_digest: Digest
    environment: Environment
    report: SuiteReport


class Approval(Versioned):
    expected_generation: int = Field(ge=0, le=MAX_EVENTS)
    approved_by: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("approved_by", "reason")
    @classmethod
    def visible_text(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("approval requires visible text")
        return value


class BaselineEvent(Versioned):
    generation: int = Field(ge=1, le=MAX_EVENTS)
    action: Literal["promote", "rollback"]
    build: Label
    build_digest: Digest
    policy: DecisionPolicy
    approval: Approval
    restored_generation: int | None = None
    recorded_at: str


class BuildComparison(Versioned):
    baseline_generation: int
    baseline_build: Label
    baseline_digest: Digest
    candidate_build: Label
    candidate_digest: Digest
    statistics: StatisticalReport


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never initialize or migrate an arbitrary existing database.
    with path.open("xb"):
        pass
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(
            f"""
            PRAGMA application_id={APPLICATION_ID};
            PRAGMA user_version=1;
            CREATE TABLE builds(label TEXT PRIMARY KEY, digest TEXT NOT NULL,
                                payload TEXT NOT NULL);
            CREATE TABLE events(generation INTEGER PRIMARY KEY, digest TEXT NOT NULL,
                                payload TEXT NOT NULL);
            CREATE TABLE comparisons(id INTEGER PRIMARY KEY, digest TEXT NOT NULL,
                                     payload TEXT NOT NULL);
            """
        )
        for table in ("builds", "events", "comparisons"):
            for operation in ("UPDATE", "DELETE"):
                connection.execute(
                    f"CREATE TRIGGER immutable_{table}_{operation} BEFORE {operation} ON {table} "
                    "BEGIN SELECT RAISE(ABORT, 'immutable history'); END"
                )


@contextmanager
def _connect(path: Path, *, write: bool = False):
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected an initialized local catalog")
    # mode=rw avoids accidentally recreating a removed catalog.
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5)
    try:
        connection.execute("PRAGMA trusted_schema=OFF")
        if (
            connection.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
            or connection.execute("PRAGMA user_version").fetchone()[0] != 1
        ):
            raise ValueError("unsupported catalog")
        connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _decode(row, contract):
    if row is None or len(row[1]) > MAX_SNAPSHOT:
        raise ValueError("missing or oversized catalog record")
    item = contract.model_validate_json(row[1])
    if digest(item) != row[0]:
        raise ValueError("catalog integrity check failed")
    return item


def _build(connection, label: str) -> Build:
    item = _decode(
        connection.execute("SELECT digest,payload FROM builds WHERE label=?", (label,)).fetchone(),
        Build,
    )
    if item.label != label:
        raise ValueError("catalog label mismatch")
    return item


def _event(connection, generation: int | None = None) -> BaselineEvent:
    if generation is None:
        generation = connection.execute("SELECT max(generation) FROM events").fetchone()[0]
    item = _decode(
        connection.execute(
            "SELECT digest,payload FROM events WHERE generation=?", (generation,)
        ).fetchone(),
        BaselineEvent,
    )
    if item.generation != generation or item.approval.expected_generation != generation - 1:
        raise ValueError("catalog generation mismatch")
    if digest(_build(connection, item.build)) != item.build_digest:
        raise ValueError("baseline build changed")
    return item


def add_build(path: Path, bundle: Path, label: str, role: Role = "candidate") -> Build:
    # Validate labels before any expensive read. Snapshot once to avoid hash/read races.
    from pydantic import TypeAdapter

    TypeAdapter(Label).validate_python(label, strict=True)
    TypeAdapter(Role).validate_python(role, strict=True)
    with tempfile.TemporaryDirectory(prefix="simweave-import-") as temporary:
        snapshot = Path(temporary) / "evidence.zip"
        sha = hashlib.sha256()
        total = 0
        with bundle.open("rb") as source, snapshot.open("xb") as target:
            while chunk := source.read(64 * 1024):
                total += len(chunk)
                if total > MAX_TOTAL:
                    raise ValueError("bundle exceeds limit")
                sha.update(chunk)
                target.write(chunk)
        manifest, report = read_bundle(snapshot)
    build = Build(
        label=label,
        role=role,
        bundle_digest=sha.hexdigest(),
        environment=manifest.environment,
        report=report,
    )
    payload = canonical(build.model_dump())
    if len(payload.encode()) > MAX_SNAPSHOT:
        raise ValueError("snapshot exceeds limit")
    with _connect(path, write=True) as connection:
        if connection.execute("SELECT count(*) FROM builds").fetchone()[0] >= MAX_BUILDS:
            raise ValueError("catalog build limit reached")
        connection.execute("INSERT INTO builds VALUES(?,?,?)", (label, digest(build), payload))
    return build


def change_baseline(
    path: Path,
    approval: Approval,
    *,
    build: str | None = None,
    policy: DecisionPolicy | None = None,
    restore: int | None = None,
) -> BaselineEvent:
    approval = Approval.model_validate(approval.model_dump())
    if (restore is None) == (build is None) or (restore is None) != (policy is not None):
        raise ValueError("choose a build and policy, or an earlier approval to restore")
    with _connect(path, write=True) as connection:
        generation = connection.execute(
            "SELECT coalesce(max(generation),0) FROM events"
        ).fetchone()[0]
        if generation != approval.expected_generation or generation >= MAX_EVENTS:
            raise ValueError("stale approval generation or event limit")
        if restore is not None:
            old = _event(connection, restore)
            build, policy = old.build, old.policy
        target = _build(connection, build)
        if any(
            c.summary is None or not c.summary.result.passed
            for c in target.report.cases
            if c.role == target.role
        ):
            raise ValueError("baseline requires complete recordings and passing quality gates")
        event = BaselineEvent(
            generation=generation + 1,
            action="rollback" if restore is not None else "promote",
            build=target.label,
            build_digest=digest(target),
            policy=policy,
            approval=approval,
            restored_generation=restore,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        connection.execute(
            "INSERT INTO events VALUES(?,?,?)",
            (event.generation, digest(event), canonical(event.model_dump())),
        )
    return event


def compare_build(path: Path, candidate: str, generation: int | None = None) -> BuildComparison:
    with _connect(path) as connection:
        event = _event(connection, generation)
        baseline = _build(connection, event.build)
        contender = _build(connection, candidate)
    result = BuildComparison(
        baseline_generation=event.generation,
        baseline_build=baseline.label,
        baseline_digest=digest(baseline),
        candidate_build=contender.label,
        candidate_digest=digest(contender),
        statistics=analyze(
            baseline.report,
            contender.report,
            event.policy,
            baseline_role=baseline.role,
            candidate_role=contender.role,
            environments=(baseline.environment, contender.environment),
        ),
    )
    with _connect(path, write=True) as connection:
        if connection.execute("SELECT count(*) FROM comparisons").fetchone()[0] >= MAX_COMPARISONS:
            raise ValueError("catalog comparison limit reached")
        connection.execute(
            "INSERT INTO comparisons(digest,payload) VALUES(?,?)",
            (digest(result), canonical(result.model_dump())),
        )
    return result


def snapshot(path: Path) -> dict:
    """Export bounded metadata and verify stored digests; no local paths in output."""
    with _connect(path) as connection:
        # Validate one report at a time instead of retaining up to 100 full reports.
        builds = []
        for row in connection.execute(
            "SELECT label FROM builds ORDER BY rowid LIMIT ?", (MAX_BUILDS + 1,)
        ):
            b = _build(connection, row[0])
            builds.append(
                {
                    "label": b.label,
                    "digest": digest(b),
                    "role": b.role,
                    "bundle_digest": b.bundle_digest,
                    "source_revision": b.environment.source_revision,
                }
            )
        events = [
            _event(connection, row[0])
            for row in connection.execute(
                "SELECT generation FROM events ORDER BY generation LIMIT ?", (MAX_EVENTS + 1,)
            )
        ]
        comparisons = [
            _decode(row, BuildComparison)
            for row in connection.execute(
                "SELECT digest,payload FROM comparisons ORDER BY id LIMIT ?", (MAX_COMPARISONS + 1,)
            )
        ]
    if len(builds) > MAX_BUILDS or len(events) > MAX_EVENTS or len(comparisons) > MAX_COMPARISONS:
        raise ValueError("catalog limits exceeded")
    return {
        "schema_version": 1,
        "generation": events[-1].generation if events else 0,
        "active_baseline": events[-1].build if events else None,
        "builds": builds,
        "events": [e.model_dump() for e in events],
        "comparisons": [c.model_dump() for c in comparisons],
    }
