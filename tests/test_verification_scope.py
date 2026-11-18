import json

from test_sweep_diff import source

from simweave.bundle_identity import bundle_identity
from simweave.cli import main
from simweave.plan_bundle import create_bundle, encode_bundle
from simweave.sweep_diff import render_plan_diff, render_plan_diff_csv


def test_success_scope_is_derived_from_completed_checks(tmp_path, capsys):
    a, b = source(), source(seeds=[9])
    bundle = create_bundle(a, b)
    left, right, path, record = [tmp_path / n for n in ("a", "b", "bundle", "identity")]
    left.write_text(a.model_dump_json())
    right.write_text(b.model_dump_json())
    path.write_bytes(encode_bundle(bundle))
    identity = bundle_identity(bundle)
    record.write_text(json.dumps(identity))
    saved = {p: p.read_bytes() for p in (left, right, path, record)}
    commands = [
        (["sweep-bundle-verify", path], False),
        (["sweep-bundle-verify-sources", path, left, right], True),
    ]
    for format, render in [
        ("html", lambda: render_plan_diff(a, b, schema_version=2)),
        ("csv", lambda: render_plan_diff_csv(a, b)),
    ]:
        output = tmp_path / format
        output.write_text(render(), encoding="utf-8", newline="")
        saved[output] = output.read_bytes()
        base = ["sweep-bundle-verify-" + format, path, output]
        commands.extend([(base, False), (base + ["--before", left, "--after", right], True)])
    for args, sources in commands:
        for gate in [[], ["--identity", record], ["--expected-sha256", identity["bundle_sha256"]]]:
            assert main(list(map(str, args + gate))) == 0
            result = json.loads(capsys.readouterr().out)
            assert result["source_checked"] is sources
            assert result["identity_checked"] is bool(gate)
        assert main(list(map(str, args + ["--expected-sha256", "0" * 64]))) == 2
        assert not capsys.readouterr().out
    replacement = create_bundle(a, a)
    path.write_bytes(encode_bundle(replacement))
    record.write_text(json.dumps(bundle_identity(replacement)))
    assert main(list(map(str, ["sweep-bundle-verify", path, "--identity", record]))) == 0
    assert json.loads(capsys.readouterr().out)["source_checked"] is False
    assert (
        main(
            list(map(str, ["sweep-bundle-verify-sources", path, left, right, "--identity", record]))
        )
        == 2
    )
    assert not capsys.readouterr().out
    for p, raw in saved.items():
        if p not in (path, record):
            assert p.read_bytes() == raw
