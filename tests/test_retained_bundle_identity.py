import json
from pathlib import Path

import pytest
from test_sweep_diff import source

from simweave.bundle_identity import (
    MAX_IDENTITY_BYTES,
    BundleIdentity,
    bundle_identity,
    read_bundle_identity,
    verify_bundle_identity_record,
)
from simweave.cli import main
from simweave.plan_bundle import create_bundle, encode_bundle


def record():
    return bundle_identity(create_bundle(source(), source(seeds=[2])))


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("schema_version", 2),
        ("canonicalization", "other"),
        ("bytes", 0),
        ("bytes", True),
        ("bytes", 1.0),
        ("bytes", 196609),
        ("bundle_sha256", "a" * 64 + "\n"),
        ("bundle_sha256", "A" * 64),
        ("interpretation", "attested"),
        ("extra", "private"),
    ],
)
def test_strict_identity(key, value):
    data = record()
    data[key] = value
    with pytest.raises(ValueError):
        read_bundle_identity(json.dumps(data).encode())


def test_schema_bounds_and_ambiguous_json(capsys):
    data = record()
    raw = json.dumps(data).encode()
    assert read_bundle_identity(raw + b" " * (MAX_IDENTITY_BYTES - len(raw))).model_dump() == data
    for key in data:
        bad = dict(data)
        del bad[key]
        with pytest.raises(ValueError):
            read_bundle_identity(json.dumps(bad).encode())
    for bad in [
        b" " * (MAX_IDENTITY_BYTES + 1),
        b"\xff",
        b"[]",
        b"[" * 2000,
        raw + b"{}",
        raw.replace(b"{", b'{"schema_version":1,', 1),
    ]:
        with pytest.raises(ValueError):
            read_bundle_identity(bad)
    assert main(["sweep-bundle-identity-schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert (
        schema
        == BundleIdentity.model_json_schema()
        == json.loads(Path("schemas/bundle-identity.schema.json").read_text())
    )
    identity = read_bundle_identity(raw)
    identity.__dict__["bytes"] = False
    with pytest.raises(ValueError):
        verify_bundle_identity_record(create_bundle(source(), source()), identity)


def test_portable_identity_file_gates(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("simweave.suites.execute", lambda *a, **k: pytest.fail("execution"))
    before, after = (
        Path("examples/plan-review/before.json"),
        Path("examples/plan-review/after.json"),
    )
    bundle, identity = tmp_path / "bundle.json", tmp_path / "identity.json"
    assert main(["sweep-bundle", str(before), str(after), "--output", str(bundle)]) == 0
    assert main(["sweep-bundle-identity", str(bundle)]) == 0
    data = json.loads(capsys.readouterr().out)
    identity.write_text(json.dumps(data, indent=4))
    snapshot = bundle.read_bytes()
    saved = identity.read_bytes()
    assert main(["sweep-bundle-verify", str(bundle), "--identity", str(identity)]) == 0
    assert (
        main(
            [
                "sweep-bundle-verify-sources",
                str(bundle),
                str(before),
                str(after),
                "--identity",
                str(identity),
            ]
        )
        == 0
    )
    for fmt in ["html", "csv"]:
        out = tmp_path / ("review." + fmt)
        args = [
            "sweep-bundle-render",
            str(bundle),
            "--format",
            fmt,
            "--identity",
            str(identity),
            "--output",
            str(out),
        ]
        assert main(args) == 0
        original = out.read_bytes()
        assert main(args) == 2 and out.read_bytes() == original
        if fmt == "csv":
            assert (
                main(
                    ["sweep-bundle-verify-csv", str(bundle), str(out), "--identity", str(identity)]
                )
                == 0
            )
    exported = tmp_path / "export.json"
    assert (
        main(
            [
                "sweep-bundle",
                str(before),
                str(after),
                "--identity",
                str(identity),
                "--output",
                str(exported),
            ]
        )
        == 0
    )
    assert exported.read_bytes() == snapshot and identity.read_bytes() == saved
    for bad in [dict(data, bytes=data["bytes"] + 1), dict(data, bundle_sha256="0" * 64)]:
        identity.write_text(json.dumps(bad))
        for cmd in ["sweep-bundle", "sweep-bundle-render"]:
            out = tmp_path / (cmd + ".blocked")
            args = [cmd, str(before), str(after)] if cmd == "sweep-bundle" else [cmd, str(bundle)]
            assert (
                main(args + ["--identity", str(identity), "--output", str(out)]) == 2
                and not out.exists()
            )
    identity.write_bytes(saved)
    bundle.write_bytes(encode_bundle(create_bundle(source(), source(seeds=[9]))))
    assert main(["sweep-bundle-verify", str(bundle)]) == 0
    assert main(["sweep-bundle-verify", str(bundle), "--identity", str(identity)]) == 2
    identity.write_bytes(b" " * (MAX_IDENTITY_BYTES + 1))
    assert main(["sweep-bundle-verify", str(bundle), "--identity", str(identity)]) == 2
    assert str(tmp_path) not in capsys.readouterr().err
    with pytest.raises(SystemExit) as error:
        main(
            [
                "sweep-bundle-verify",
                str(bundle),
                "--identity",
                str(identity),
                "--expected-sha256",
                "a" * 64,
            ]
        )
    assert error.value.code == 2
