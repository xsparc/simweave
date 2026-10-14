import json
import subprocess
from types import SimpleNamespace

import pytest

from simweave import attestation, history
from simweave.catalog_archive import export_catalog
from simweave.cli import main


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    database, archive, bundle = (
        tmp_path / "history.db",
        tmp_path / "catalog.ndjson",
        tmp_path / "bundle.jsonl",
    )
    history.initialize(database)
    export_catalog(database, archive)
    bundle.write_text('{"synthetic":"unit test only"}', encoding="utf-8")
    policy = attestation.AttestationPolicy(
        repository="example/simweave",
        workflow=".github/workflows/ci.yml",
        source_ref="refs/heads/main",
        source_digest="a" * 40,
    )
    monkeypatch.setattr(attestation.shutil, "which", lambda _: "trusted-gh")
    return archive, bundle, policy


def test_verified_snapshot_is_restored_not_changed_source(inputs, tmp_path, monkeypatch):
    archive, bundle, policy = inputs
    original = archive.read_bytes()

    def verify(command, **kwargs):
        assert command[:3] == ["trusted-gh", "attestation", "verify"]
        for flag, expected in (
            ("--hostname", "github.com"),
            ("--repo", policy.repository),
            ("--signer-workflow", policy.repository + "/" + policy.workflow),
            ("--source-ref", policy.source_ref),
            ("--source-digest", policy.source_digest),
            ("--predicate-type", "https://slsa.dev/provenance/v1"),
            ("--cert-oidc-issuer", "https://token.actions.githubusercontent.com"),
        ):
            assert command[command.index(flag) + 1] == expected
        assert "--deny-self-hosted-runners" in command
        assert kwargs["timeout"] == 60 and kwargs["shell"] is False
        assert kwargs["stdin"] == subprocess.DEVNULL
        archive.write_bytes(b"replaced while verifier runs")
        kwargs["stdout"].write(b'[{"verificationResult":{"statement":{}}}]')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(attestation.subprocess, "run", verify)
    destination = tmp_path / "restored.db"
    receipt = attestation.verify_catalog(archive, bundle, policy, destination=destination)
    assert receipt["verified"] and receipt["restored"]
    exported = tmp_path / "reexport.ndjson"
    export_catalog(destination, exported)
    assert exported.read_bytes() == original
    assert not list(tmp_path.glob("simweave-attestation-*"))


@pytest.mark.parametrize(
    "failure", ["rejected", "timeout", "malformed", "empty", "shape", "oversized"]
)
def test_verifier_failures_never_publish(inputs, tmp_path, monkeypatch, failure):
    def verify(command, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 60)
        output = {
            "malformed": b"not JSON",
            "empty": b"[]",
            "shape": b"[{}]",
            "oversized": b"x" * 100,
        }.get(failure, b"[]")
        kwargs["stdout"].write(output)
        return SimpleNamespace(returncode=1 if failure == "rejected" else 0)

    monkeypatch.setattr(attestation, "MAX_RESULT", 50)
    monkeypatch.setattr(attestation.subprocess, "run", verify)
    destination = tmp_path / "rejected.db"
    with pytest.raises(ValueError):
        attestation.verify_catalog(*inputs, destination=destination)
    assert not destination.exists()
    assert not list(tmp_path.glob("simweave-attestation-*"))


def test_missing_verifier_and_input_limits(inputs, monkeypatch):
    monkeypatch.setattr(attestation.shutil, "which", lambda _: None)
    with pytest.raises(ValueError, match="CLI"):
        attestation.verify_catalog(*inputs)
    monkeypatch.setattr(attestation.shutil, "which", lambda _: "trusted-gh")
    monkeypatch.setattr(attestation, "MAX_BUNDLE", 1)
    with pytest.raises(ValueError, match="limit"):
        attestation.verify_catalog(*inputs)


def test_cli_verification_failure_is_sanitized(inputs, tmp_path, monkeypatch, capsys):
    archive, bundle, policy = inputs
    path = tmp_path / "policy.json"
    path.write_text(policy.model_dump_json(), encoding="utf-8")

    def denied(*args, **kwargs):
        raise OSError("private operator path and token")

    monkeypatch.setattr(attestation.subprocess, "run", denied)
    assert main(["attestation", str(archive), "--bundle", str(bundle), "--policy", str(path)]) == 2
    output = capsys.readouterr()
    assert "private" not in output.err and "token" not in output.err
    assert json.loads(output.err)["error"] == "ValueError"


@pytest.mark.parametrize(
    "change",
    [
        {"repository": "https://github.com/example/repo"},
        {"workflow": "../workflow.yml"},
        {"source_ref": "refs/heads/../main"},
        {"source_digest": "latest"},
        {"extra": True},
    ],
)
def test_trust_policy_closed(inputs, change):
    with pytest.raises(ValueError):
        attestation.AttestationPolicy.model_validate({**inputs[2].model_dump(), **change})
