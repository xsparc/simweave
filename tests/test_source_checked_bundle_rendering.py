import json
from pathlib import Path

import pytest
from test_sweep_diff import source

from simweave.bundle_identity import bundle_identity
from simweave.cli import main
from simweave.plan_bundle import create_bundle, encode_bundle, read_bundle


@pytest.mark.parametrize("format", ["html", "csv"])
def test_source_checked_rendering(tmp_path, monkeypatch, capsys, format):
    monkeypatch.setattr("simweave.suites.execute", lambda *a, **k: pytest.fail("execution"))
    before, after = [Path("examples/plan-review") / n for n in ["before.json", "after.json"]]
    path, identity, out = [
        tmp_path / n for n in ["bundle.json", "identity.json", "review." + format]
    ]
    assert main(["sweep-bundle", str(before), str(after), "--output", str(path)]) == 0
    original = path.read_bytes()
    bundle = read_bundle(original)
    record = bundle_identity(bundle)
    identity.write_text(json.dumps(record))
    saved = identity.read_bytes()
    args = ["sweep-bundle-render", str(path), "--format", format, "--output", str(out)]
    assert (
        main(args + ["--before", str(before), "--identity", str(identity)]) == 2
        and not out.exists()
    )
    assert main(args + ["--after", str(after)]) == 2 and not out.exists()
    assert (
        main(args + ["--before", str(after), "--after", str(before), "--identity", str(identity)])
        == 2
        and not out.exists()
    )
    assert (
        main(
            args
            + [
                "--before",
                str(before),
                "--after",
                str(before),
                "--expected-sha256",
                record["bundle_sha256"],
            ]
        )
        == 2
        and not out.exists()
    )
    replacement = create_bundle(source(), source(seeds=[9]))
    path.write_bytes(encode_bundle(replacement))
    identity.write_text(json.dumps(bundle_identity(replacement)))
    assert main(["sweep-bundle-verify", str(path), "--identity", str(identity)]) == 0
    assert (
        main(args + ["--before", str(before), "--after", str(after), "--identity", str(identity)])
        == 2
        and not out.exists()
    )
    path.write_bytes(original)
    identity.write_bytes(saved)
    good = args + ["--before", str(before), "--after", str(after), "--identity", str(identity)]
    assert main(good) == 0
    result = out.read_bytes()
    assert main(good) == 2 and out.read_bytes() == result
    assert path.read_bytes() == original and identity.read_bytes() == saved
    large = tmp_path / "large.json"
    large.write_bytes(b" " * 65537)
    blocked = tmp_path / "blocked"
    assert (
        main(
            [
                "sweep-bundle-render",
                str(path),
                "--before",
                str(large),
                "--after",
                str(after),
                "--output",
                str(blocked),
            ]
        )
        == 2
        and not blocked.exists()
    )
    assert str(tmp_path) not in capsys.readouterr().err
