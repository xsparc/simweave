import json

from test_sweep_diff import source

from simweave.bundle_identity import read_bundle_identity
from simweave.cli import main
from simweave.plan_bundle import create_bundle, encode_bundle


def test_exclusive_identity_export(tmp_path, capsys):
    path, out = tmp_path / "bundle", tmp_path / "identity"
    raw = encode_bundle(create_bundle(source(), source(seeds=[9])))
    path.write_bytes(raw)
    assert main(["sweep-bundle-identity", str(path)]) == 0
    stdout = json.loads(capsys.readouterr().out)
    args = ["sweep-bundle-identity", str(path), "--output", str(out)]
    assert main(args) == 0
    assert capsys.readouterr().out == ""
    saved = out.read_bytes()
    assert read_bundle_identity(saved).model_dump() == stdout
    assert saved.endswith(b"\n")
    assert main(args) == 2 and out.read_bytes() == saved
    assert path.read_bytes() == raw
    path.write_bytes(b"{}")
    blocked = tmp_path / "blocked"
    assert main(["sweep-bundle-identity", str(path), "--output", str(blocked)]) == 2
    assert not blocked.exists()
    assert str(tmp_path) not in capsys.readouterr().err
