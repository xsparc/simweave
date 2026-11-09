import hashlib
import json
from pathlib import Path

import pytest
from test_sweep_diff import source

from simweave.bundle_identity import ENCODING, bundle_identity, verify_bundle_identity
from simweave.cli import main
from simweave.plan_bundle import MAX_BUNDLE, create_bundle, encode_bundle, read_bundle


def test_normalized_identity_and_replacements(monkeypatch):
    monkeypatch.setattr("simweave.suites.execute", lambda *a, **k: pytest.fail("execution"))
    before, after = source(name="café"), source(seeds=[2])
    bundle = create_bundle(before, after)
    raw = encode_bundle(bundle)
    expected = bundle_identity(bundle)
    assert expected["canonicalization"] == ENCODING
    assert expected["bytes"] == len(raw)
    assert expected["bundle_sha256"] == hashlib.sha256(raw).hexdigest()
    assert raw.endswith(b"\n") and b"caf\\u00e9" in raw
    pretty = json.dumps(bundle.model_dump(), indent=4, ensure_ascii=False).encode()
    assert bundle_identity(read_bundle(pretty)) == expected
    assert hashlib.sha256(pretty).hexdigest() != expected["bundle_sha256"]
    verify_bundle_identity(bundle, expected["bundle_sha256"])
    for replacement in [
        create_bundle(after, before),
        create_bundle(before, before),
        create_bundle(before, source(seeds=[3])),
    ]:
        assert read_bundle(encode_bundle(replacement))
        with pytest.raises(ValueError):
            verify_bundle_identity(replacement, expected["bundle_sha256"])
    bundle.before.seeds.append(99)
    with pytest.raises(ValueError):
        bundle_identity(bundle)


@pytest.mark.parametrize("expected", ["", "0" * 63, "A" * 64, "z" * 64, "0" * 64 + "\n", None, 1])
def test_strict_digest(expected):
    with pytest.raises(ValueError):
        verify_bundle_identity(create_bundle(source(), source()), expected)


def test_cli_portable_identity_gates(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("simweave.suites.execute", lambda *a, **k: pytest.fail("execution"))
    before, after = (
        Path("examples/plan-review/before.json"),
        Path("examples/plan-review/after.json"),
    )
    bundle = tmp_path / "bundle.json"
    export = ["sweep-bundle", str(before), str(after), "--output", str(bundle)]
    assert main(export) == 0
    original = bundle.read_bytes()
    assert main(["sweep-bundle-identity", str(bundle)]) == 0
    identity = json.loads(capsys.readouterr().out)
    digest = identity["bundle_sha256"]
    assert main(["sweep-bundle-verify", str(bundle), "--expected-sha256", digest]) == 0
    assert (
        main(
            [
                "sweep-bundle-verify-sources",
                str(bundle),
                str(before),
                str(after),
                "--expected-sha256",
                digest,
            ]
        )
        == 0
    )
    csv = tmp_path / "review.csv"
    assert (
        main(
            [
                "sweep-bundle-render",
                str(bundle),
                "--format",
                "csv",
                "--output",
                str(csv),
                "--expected-sha256",
                digest,
            ]
        )
        == 0
    )
    assert (
        main(["sweep-bundle-verify-csv", str(bundle), str(csv), "--expected-sha256", digest]) == 0
    )
    for command in ["sweep-bundle-render", "sweep-bundle"]:
        output = tmp_path / (command + ".out")
        args = (
            [command, str(bundle)]
            if command.endswith("render")
            else [command, str(before), str(after)]
        ) + ["--output", str(output), "--expected-sha256", "0" * 64]
        assert main(args) == 2 and not output.exists()
        output.write_bytes(b"preserve")
        assert main(args) == 2 and output.read_bytes() == b"preserve"
    assert main(export + ["--expected-sha256", digest]) == 2 and bundle.read_bytes() == original
    replacement = create_bundle(source(), source(seeds=[9]))
    bundle.write_bytes(encode_bundle(replacement))
    assert main(["sweep-bundle-verify", str(bundle)]) == 0
    assert main(["sweep-bundle-verify", str(bundle), "--expected-sha256", digest]) == 2
    for raw in [b"{}", b" " * (MAX_BUNDLE + 1)]:
        bundle.write_bytes(raw)
        assert main(["sweep-bundle-identity", str(bundle)]) == 2
        assert bundle.read_bytes() == raw
    assert str(tmp_path) not in capsys.readouterr().err


def test_identity_output_limit(monkeypatch):
    bundle = create_bundle(source(), source())
    monkeypatch.setattr("simweave.plan_bundle.MAX_BUNDLE", 1)
    with pytest.raises(ValueError):
        bundle_identity(bundle)
