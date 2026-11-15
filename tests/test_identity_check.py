import json

from simweave.cli import main


def test_identity_check_is_bounded_read_only_and_not_a_bundle_match(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        "simweave.suites.execute",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("simulation")),
    )
    path = tmp_path / "identity"
    record = {
        "schema_version": 1,
        "canonicalization": "simweave-plan-bundle-json-v1",
        "bundle_sha256": "a" * 64,
        "bytes": 123,
        "interpretation": "retained_identity_not_attestation",
    }
    raw = json.dumps(record).encode()
    path.write_bytes(raw)
    assert main(["sweep-bundle-identity-check", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "schema_version": 1,
        "valid": True,
        "interpretation": "identity_record_validity_only",
    }
    assert path.read_bytes() == raw
    invalid = [
        b"{}",
        b"[]",
        b"\xff",
        raw + b"{}",
        raw.replace(b"{", b'{"schema_version":1,', 1),
        b" " * 4097,
    ]
    for key, value in [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("schema_version", 2),
        ("bundle_sha256", "A" * 64),
        ("bundle_sha256", "a" * 64 + "\n"),
        ("bytes", 0),
        ("bytes", True),
        ("bytes", 1.0),
        ("bytes", 10**10),
        ("extra", "value"),
    ]:
        invalid.append(json.dumps({**record, key: value}).encode())
    for bad in invalid:
        path.write_bytes(bad)
        assert main(["sweep-bundle-identity-check", str(path)]) == 2
        assert path.read_bytes() == bad
        output = capsys.readouterr()
        assert not output.out and str(tmp_path) not in output.err
    path.write_bytes(raw + b" " * (4096 - len(raw)))
    assert main(["sweep-bundle-identity-check", str(path)]) == 0
