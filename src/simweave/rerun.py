"""Explicit local-image reruns; archive data never selects executable code or mounts."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from simweave.bundles import read_bundle
from simweave.contracts import canonical
from simweave.provenance import capture, mismatches
from simweave.suites import execute_suite, review


def rerun_here(bundle: Path, output: Path) -> int:
    """Run inside an operator-selected image after checking actual installed runtime."""
    manifest, original = read_bundle(bundle)
    current = capture(manifest.environment.source_revision, manifest.environment.image_id)
    differences = mismatches(manifest.environment, current)
    if differences:
        output.mkdir(parents=True, exist_ok=False)
        (output / "reproduction.json").write_text(
            canonical(
                {
                    "schema_version": 1,
                    "status": "environment_mismatch",
                    "mismatches": differences,
                }
            ),
            encoding="utf-8",
        )
        return 2
    fresh = execute_suite(original.suite, output, environment=current)
    cases = []
    for old, new in zip(original.cases, fresh.cases, strict=True):
        cases.append(
            {
                "id": old.id,
                "telemetry_matches": bool(
                    old.summary
                    and new.summary
                    and old.summary.result.telemetry_digest == new.summary.result.telemetry_digest
                ),
                "result_matches": bool(
                    old.summary and new.summary and old.summary.result == new.summary.result
                ),
                "original_error": old.error,
                "rerun_error": new.error,
            }
        )
    incomplete = any(c["original_error"] or c["rerun_error"] for c in cases)
    matched = all(c["telemetry_matches"] and c["result_matches"] for c in cases)
    verdict = {
        "schema_version": 1,
        "status": "incomplete" if incomplete else "reproduced" if matched else "different",
        "original_exit_code": review(original).exit_code,
        "rerun_exit_code": review(fresh).exit_code,
        "cases": cases,
    }
    (output / "reproduction.json").write_text(canonical(verdict), encoding="utf-8")
    return 2 if incomplete else 0 if matched else 1


def _docker(*args: str, timeout: int = 60, check: bool = True) -> subprocess.CompletedProcess:
    try:
        completed = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("container operation failed") from exc
    if check and completed.returncode:
        # Do not forward daemon diagnostics, host paths, or image-supplied logs.
        raise RuntimeError("container operation failed")
    return completed


def rerun_container(bundle: Path, image_id: str, output: Path) -> int:
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
        raise ValueError("rerun requires a local image ID")
    manifest, _ = read_bundle(bundle)
    if manifest.environment.image_id != image_id:
        raise ValueError("selected image does not match recorded image identity")
    installed = _docker("image", "inspect", "--format", "{{.Id}}", image_id).stdout.strip()
    if installed != image_id:
        raise ValueError("installed image identity differs")
    output.mkdir(parents=True, exist_ok=False)
    name = "simweave-rerun-" + uuid.uuid4().hex
    created = False
    try:
        _docker(
            "create",
            "--name",
            name,
            "--pull",
            "never",
            "--network",
            "none",
            "--user",
            "10001:10001",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "256",
            "--memory",
            "4g",
            "--cpus",
            "2",
            "--workdir",
            "/tmp",
            "--env",
            "HOME=/tmp",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            image_id,
            "python",
            "-m",
            "simweave.cli",
            "_bundle-rerun",
            "/tmp/simweave-input.zip",
            "--output",
            "/tmp/simweave-rerun",
        )
        created = True
        # Copy a regular, world-readable snapshot, with no bind mounts or inherited
        # input-file permissions. The child validates the snapshot again.
        with tempfile.TemporaryDirectory(prefix="simweave-bundle-") as temporary:
            snapshot = Path(temporary) / "input.zip"
            snapshot.write_bytes(bundle.read_bytes())
            snapshot.chmod(0o644)
            _docker("cp", str(snapshot), name + ":/tmp/simweave-input.zip")
        completed = _docker("start", "--attach", name, timeout=3600, check=False)
        if completed.returncode not in (0, 1, 2):
            raise RuntimeError("container execution failed")
        _docker("cp", name + ":/tmp/simweave-rerun/.", str(output.resolve()))
        verdict = json.loads((output / "reproduction.json").read_text(encoding="utf-8"))
        expected = {"reproduced": 0, "different": 1, "incomplete": 2, "environment_mismatch": 2}
        if expected.get(verdict.get("status")) != completed.returncode:
            raise RuntimeError("invalid reproduction verdict")
        return completed.returncode
    finally:
        if created:
            _docker("rm", "--force", name)
