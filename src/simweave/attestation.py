"""Operator-only GitHub attestation verification with immutable input snapshots."""

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from pydantic import Field, model_validator

from simweave.catalog_archive import MAX_ARCHIVE, restore_catalog
from simweave.provenance import Revision
from simweave.statistics import Versioned

MAX_BUNDLE = 4 * 1024 * 1024
MAX_RESULT = 8 * 1024 * 1024


class AttestationPolicy(Versioned):
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", max_length=200)
    workflow: str = Field(pattern=r"^\.github/workflows/[A-Za-z0-9_-]+\.ya?ml$", max_length=200)
    source_ref: str = Field(pattern=r"^refs/(heads|tags)/[A-Za-z0-9._/-]+$", max_length=250)
    source_digest: Revision

    @model_validator(mode="after")
    def valid_ref(self):
        if ".." in self.source_ref or self.source_ref.endswith(("/", ".", ".lock")):
            raise ValueError("invalid source ref")
        return self


def _snapshot(source: Path, destination: Path, maximum: int) -> str:
    sha, total = hashlib.sha256(), 0
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        while chunk := incoming.read(65536):
            total += len(chunk)
            if total > maximum:
                raise ValueError("attestation input exceeds limit")
            sha.update(chunk)
            outgoing.write(chunk)
    if not total:
        raise ValueError("empty attestation input")
    return sha.hexdigest()


def verify_catalog(
    archive: Path, bundle: Path, policy: AttestationPolicy, *, destination: Path | None = None
) -> dict:
    """Only gh's successful verification permits restore of the same snapshotted bytes.

    This may fetch public Sigstore trust material. It does not claim offline operation.
    GitHub CLI and the local executable search path are trusted operator dependencies.
    """
    policy = AttestationPolicy.model_validate(policy.model_dump())
    executable = shutil.which("gh")
    if executable is None:
        raise ValueError("GitHub CLI with attestation support is required")
    with tempfile.TemporaryDirectory(prefix="simweave-attestation-") as folder:
        root = Path(folder)
        artifact, proof, result = (
            root / "catalog.ndjson",
            root / "bundle.jsonl",
            root / "result.json",
        )
        artifact_digest = _snapshot(archive, artifact, MAX_ARCHIVE)
        proof_digest = _snapshot(bundle, proof, MAX_BUNDLE)
        command = [
            executable,
            "attestation",
            "verify",
            str(artifact),
            "--bundle",
            str(proof),
            "--hostname",
            "github.com",
            "--repo",
            policy.repository,
            "--signer-workflow",
            f"{policy.repository}/{policy.workflow}",
            "--source-ref",
            policy.source_ref,
            "--source-digest",
            policy.source_digest,
            "--cert-oidc-issuer",
            "https://token.actions.githubusercontent.com",
            "--predicate-type",
            "https://slsa.dev/provenance/v1",
            "--deny-self-hosted-runners",
            "--format",
            "json",
        ]
        try:
            with result.open("xb") as output:
                completed = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.DEVNULL,
                    timeout=60,
                    check=False,
                    shell=False,
                )
            if completed.returncode != 0 or result.stat().st_size > MAX_RESULT:
                raise ValueError("attestation verification rejected")
            verified = json.loads(result.read_bytes())
            if (
                not isinstance(verified, list)
                or not verified
                or any(
                    not isinstance(v, dict) or not isinstance(v.get("verificationResult"), dict)
                    for v in verified
                )
            ):
                raise ValueError("unsupported verifier result")
        except (OSError, subprocess.SubprocessError, ValueError, RecursionError):
            raise ValueError("attestation verification failed") from None
        receipt = {
            "schema_version": 1,
            "verified": True,
            "verifier": "gh-attestation",
            "artifact_sha256": artifact_digest,
            "bundle_sha256": proof_digest,
            "policy": policy.model_dump(),
            "restored": destination is not None,
        }
        if destination is not None:
            receipt["catalog"] = restore_catalog(artifact, destination)
        return receipt


def register(commands):
    command = commands.add_parser(
        "attestation", help="verify GitHub provenance or restore verified catalog"
    )
    command.add_argument("path", type=Path)
    command.add_argument("--bundle", required=True, type=Path)
    command.add_argument("--policy", required=True, type=Path)
    command.add_argument(
        "--restore", type=Path, help="fresh destination database after verification"
    )


def dispatch(args):
    with args.policy.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("attestation policy too large")
    policy = AttestationPolicy.model_validate_json(raw)
    print(json.dumps(verify_catalog(args.path, args.bundle, policy, destination=args.restore)))
    return 0
