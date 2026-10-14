"""Bounded data-only bundles. No archive filename is ever extracted or executed."""

from __future__ import annotations

import hashlib
import io
import stat
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from simweave.comparison import PreviewPoint, preview_steps
from simweave.contracts import Contract, RunResult, Sample, Scenario
from simweave.engine import verify_recording
from simweave.provenance import Digest, Environment
from simweave.suites import SuiteReport

MAX_TOTAL = 128 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
MAX_REPORT = 4 * 1024 * 1024
MAX_MANIFEST = 64 * 1024


class Member(Contract):
    sha256: Digest
    size: int = Field(ge=0, le=MAX_MEMBER)


class Manifest(Contract):
    schema_version: Literal[1] = 1
    environment: Environment
    files: dict[str, Member] = Field(min_length=1, max_length=193)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("bundle version must be an integer")
        return value


def members(report: SuiteReport) -> set[str]:
    names = {"report.json"}
    for case in report.cases:
        if case.summary:
            names.update(
                f"{case.id}/{name}" for name in ("scenario.json", "result.json", "telemetry.jsonl")
            )
    return names


def write_bundle(report: SuiteReport, environment: Environment, directory: Path) -> Path:
    """Package only known suite outputs. Exclude partial execution-error recordings."""
    files = {}
    for name in sorted(members(report)):
        path = directory / name
        if path.is_symlink() or path.stat().st_size > MAX_MEMBER:
            raise ValueError("invalid recording member")
        data = path.read_bytes()
        files[name] = Member(size=len(data), sha256=hashlib.sha256(data).hexdigest())
    manifest = Manifest(environment=environment, files=files)
    if files["report.json"].size > MAX_REPORT or sum(m.size for m in files.values()) > MAX_TOTAL:
        raise ValueError("bundle exceeds size limit")
    output = directory / "evidence.zip"
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest.model_dump_json())
        for name in sorted(files):
            # Write bytes rather than inheriting local paths, permissions or timestamps.
            archive.writestr(name, (directory / name).read_bytes())
    return output


def read_bundle(path: Path) -> tuple[Manifest, SuiteReport]:
    try:
        return _read_bundle(path)
    except (zipfile.BadZipFile, UnicodeError, EOFError, struct.error, zlib.error) as exc:
        raise ValueError("invalid bundle") from exc


def _read_bundle(path: Path) -> tuple[Manifest, SuiteReport]:
    size = path.stat().st_size
    if not 22 <= size <= MAX_TOTAL:
        raise ValueError("bundle exceeds size limit")
    # Version 1 uses ordinary single-disk ZIP with no archive comment. Bound the
    # central directory before ZipFile allocates one object per attacker-supplied entry.
    with path.open("rb") as stream:
        stream.seek(-22, 2)
        signature, disk, start_disk, count_disk, count, central_size, offset, comment = (
            struct.unpack("<4s4H2LH", stream.read(22))
        )
    if (
        signature != b"PK\x05\x06"
        or disk
        or start_disk
        or comment
        or not 2 <= count == count_disk <= 194
        or central_size > 65536
        or offset + central_size != size - 22
    ):
        raise ValueError("invalid bundle directory")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(infos) != count or len(set(names)) != len(names):
            raise ValueError("invalid bundle member count")
        total = 0
        for info in infos:
            mode = info.external_attr >> 16
            if (
                info.file_size > MAX_MEMBER
                or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                or info.flag_bits & 1
                or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))
            ):
                raise ValueError("invalid bundle member")
            total += info.file_size
        if total > MAX_TOTAL or "manifest.json" not in names or "report.json" not in names:
            raise ValueError("invalid bundle contents")
        if archive.getinfo("manifest.json").file_size > MAX_MANIFEST:
            raise ValueError("manifest exceeds size limit")
        manifest = Manifest.model_validate_json(archive.read("manifest.json"))
        if set(names) != set(manifest.files) | {"manifest.json"}:
            raise ValueError("bundle member set differs from manifest")
        for name, expected in manifest.files.items():
            if archive.getinfo(name).file_size != expected.size:
                raise ValueError("bundle member size mismatch")
            digest = hashlib.sha256()
            with archive.open(name) as stream:
                while block := stream.read(65536):
                    digest.update(block)
            if digest.hexdigest() != expected.sha256:
                raise ValueError("bundle member checksum mismatch")
        if manifest.files["report.json"].size > MAX_REPORT:
            raise ValueError("report exceeds size limit")
        report = SuiteReport.model_validate_json(archive.read("report.json"))
        if set(manifest.files) != members(report):
            raise ValueError("unexpected bundle member")
        for case in report.cases:
            if not case.summary:
                continue
            scenario = Scenario.model_validate_json(archive.read(f"{case.id}/scenario.json"))
            result = RunResult.model_validate_json(archive.read(f"{case.id}/result.json"))
            if scenario != case.scenario or result != case.summary.result:
                raise ValueError("recording differs from report")
            keep, points = preview_steps(scenario.world.steps), []
            with archive.open(f"{case.id}/telemetry.jsonl") as raw, io.TextIOWrapper(raw) as stream:

                def samples(stream=stream, keep=keep, points=points):
                    for line in stream:
                        sample = Sample.model_validate_json(line)
                        if sample.step in keep:
                            points.append(
                                PreviewPoint(
                                    step=sample.step, time=sample.time, position=sample.position
                                )
                            )
                        yield sample

                verify_recording(scenario, result, samples())
            if points != case.summary.trajectory:
                raise ValueError("preview differs from verified telemetry")
        return manifest, report
