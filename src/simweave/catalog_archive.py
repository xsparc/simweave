"""Streaming data archives; never execute imported SQL or extract archive paths."""

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from simweave import history
from simweave.contracts import canonical

MAX_ARCHIVE = 512 * 1024 * 1024
MAX_LINE = history.MAX_SNAPSHOT + 1024
HEADER = {"schema_version": 1, "format": "simweave-catalog-ndjson"}
TABLES = (
    ("builds", "label", history.Build, history.MAX_BUILDS),
    ("events", "generation", history.BaselineEvent, history.MAX_EVENTS),
    ("comparisons", "id", history.BuildComparison, history.MAX_COMPARISONS),
)


def _references(connection, item):
    if isinstance(item, history.Build):
        return
    if isinstance(item, history.BaselineEvent):
        build = history._build(connection, item.build)
        if history.digest(build) != item.build_digest or any(
            c.summary is None or not c.summary.result.passed
            for c in build.report.cases
            if c.role == build.role
        ):
            raise ValueError("invalid baseline build")
        if item.approval.expected_generation != item.generation - 1:
            raise ValueError("invalid approval generation")
        if datetime.fromisoformat(item.recorded_at).tzinfo is None:
            raise ValueError("approval timestamp requires timezone")
        if item.action == "promote":
            if item.restored_generation is not None:
                raise ValueError("promotion cannot restore an event")
        else:
            if (
                item.restored_generation is None
                or not 1 <= item.restored_generation < item.generation
            ):
                raise ValueError("invalid rollback reference")
            old = history._event(connection, item.restored_generation)
            if (old.build, old.policy) != (item.build, item.policy):
                raise ValueError("rollback changed approved policy")
        return
    event = history._event(connection, item.baseline_generation)
    baseline = history._build(connection, item.baseline_build)
    candidate = history._build(connection, item.candidate_build)
    stats = item.statistics
    if (
        event.build != baseline.label
        or item.baseline_digest != history.digest(baseline)
        or item.candidate_digest != history.digest(candidate)
        or stats.policy != event.policy
        or stats.policy_digest != event.policy.digest()
        or stats.baseline_role != baseline.role
        or stats.candidate_role != candidate.role
        or stats.baseline_environment != baseline.environment
        or stats.candidate_environment != candidate.environment
        or stats.baseline_report_digest != history.digest(baseline.report)
        or stats.candidate_report_digest != history.digest(candidate.report)
        or stats.baseline_suite_digest != baseline.report.suite.digest()
        or stats.candidate_suite_digest != candidate.report.suite.digest()
    ):
        raise ValueError("comparison references changed")


def export_catalog(database: Path, output: Path) -> dict:
    """One read transaction, bounded memory, publish complete output without overwrite."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".catalog-export-", dir=output.parent) as folder:
        temporary = Path(folder) / "archive.ndjson"
        sha, total, counts = hashlib.sha256(), 0, {}
        with temporary.open("xb") as stream, history._connect(database) as connection:

            def write(value):
                nonlocal total
                line = (canonical(value) + "\n").encode()
                total += len(line)
                if len(line) > MAX_LINE or total > MAX_ARCHIVE - 1024:
                    raise ValueError("catalog archive exceeds limit")
                stream.write(line)
                sha.update(line)

            write(HEADER)
            for table, key, contract, limit in TABLES:
                count = 0
                for identifier, digest, payload in connection.execute(
                    f"SELECT {key},digest,payload FROM {table} ORDER BY rowid LIMIT ?",
                    (limit + 1,),
                ):
                    count += 1
                    if count > limit:
                        raise ValueError("catalog record limit exceeded")
                    item = history._decode((digest, payload), contract)
                    if table != "builds" and identifier != count:
                        raise ValueError("noncontiguous catalog history")
                    if table != "comparisons" and getattr(item, key) != identifier:
                        raise ValueError("catalog key mismatch")
                    _references(connection, item)
                    write(
                        {
                            "table": table,
                            "key": identifier,
                            "digest": digest,
                            "payload": item.model_dump(),
                        }
                    )
                counts[table] = count
            footer = {"sha256": sha.hexdigest(), "counts": counts}
            stream.write((canonical(footer) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    return footer


def restore_catalog(archive: Path, database: Path) -> dict:
    """Validate into a fresh private staging DB; a failed restore publishes nothing."""
    database.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".catalog-restore-", dir=database.parent) as folder:
        temporary = Path(folder) / "catalog.sqlite3"
        history.initialize(temporary)
        sha, total = hashlib.sha256(), 0
        counts = {t[0]: 0 for t in TABLES}
        phase = 0
        with archive.open("rb") as stream, history._connect(temporary, write=True) as connection:

            def read():
                nonlocal total
                line = stream.readline(MAX_LINE + 1)
                total += len(line)
                if not line.endswith(b"\n") or len(line) > MAX_LINE or total > MAX_ARCHIVE:
                    raise ValueError("truncated or oversized archive")
                try:
                    value = json.loads(line)
                except RecursionError:
                    raise ValueError("archive nesting exceeds limit") from None
                # Canonical bytes reject duplicate JSON keys and ambiguous representations.
                if line != (canonical(value) + "\n").encode():
                    raise ValueError("noncanonical archive record")
                return line, value

            line, header = read()
            if header != HEADER or type(header.get("schema_version")) is not int:
                raise ValueError("unsupported catalog archive")
            sha.update(line)
            while True:
                line, record = read()
                if isinstance(record, dict) and set(record) == {"sha256", "counts"}:
                    expected = {"sha256": sha.hexdigest(), "counts": counts}
                    if line != (canonical(expected) + "\n").encode() or stream.read(1):
                        raise ValueError("archive checksum or count mismatch")
                    break
                if not isinstance(record, dict) or set(record) != {
                    "table",
                    "key",
                    "digest",
                    "payload",
                }:
                    raise ValueError("invalid archive record")
                while phase < len(TABLES) and TABLES[phase][0] != record["table"]:
                    phase += 1
                if phase == len(TABLES):
                    raise ValueError("unexpected archive table order")
                table, key, contract, limit = TABLES[phase]
                counts[table] += 1
                if counts[table] > limit:
                    raise ValueError("archive record limit exceeded")
                item = history._decode((record["digest"], canonical(record["payload"])), contract)
                identifier = record["key"]
                if table != "builds" and (
                    type(identifier) is not int or identifier != counts[table]
                ):
                    raise ValueError("noncontiguous archive history")
                if table != "comparisons" and getattr(item, key) != identifier:
                    raise ValueError("archive key mismatch")
                _references(connection, item)
                connection.execute(
                    f"INSERT INTO {table} VALUES(?,?,?)",
                    (identifier, record["digest"], canonical(item.model_dump())),
                )
                sha.update(line)
        # Hard link is atomic and fails if the destination already exists, including symlinks.
        # Staging is on the same filesystem. Unsupported filesystems fail closed.
        os.link(temporary, database)
    return record
