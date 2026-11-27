import json
from pathlib import Path

import pytest
from test_sweep_diff import source

from simweave.bundle_identity import bundle_identity
from simweave.cli import main
from simweave.plan_bundle import create_bundle, encode_bundle
from simweave.sweep_diff import render_plan_diff, render_plan_diff_csv
from simweave.verification_response import (
    MAX_VERIFICATION_RESPONSE_BYTES,
    read_bundle_verification_response,
)


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
            raw = capsys.readouterr().out.encode()
            result = read_bundle_verification_response(raw)
            assert result.model_dump() == {
                "schema_version": 1,
                "verified": True,
                "source_checked": sources,
                "identity_checked": bool(gate),
                "interpretation": "local_source_consistency_only",
            }
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


def test_verification_response_schema_matches_cli(capsys):
    assert main(["sweep-bundle-verification-schema"]) == 0
    emitted = json.loads(capsys.readouterr().out)
    checked_in = (
        Path(__file__).resolve().parents[1] / "schemas/bundle-verification-response.schema.json"
    )
    assert emitted == json.loads(checked_in.read_text(encoding="utf-8"))
    assert emitted["additionalProperties"] is False
    assert set(emitted["required"]) == set(emitted["properties"])


VALID = {
    "schema_version": 1,
    "verified": True,
    "source_checked": False,
    "identity_checked": False,
    "interpretation": "local_source_consistency_only",
}


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("schema_version", "1"),
        ("schema_version", 2),
        ("verified", 1),
        ("verified", False),
        ("source_checked", "false"),
        ("identity_checked", 0),
        ("interpretation", "external_provenance"),
        ("unknown", "synthetic_private_value"),
    ],
)
def test_response_reader_rejects_incorrect_types_or_claims_without_echo(field, value):
    raw = json.dumps({**VALID, field: value}).encode()
    with pytest.raises(ValueError, match="^invalid bundle verification response$"):
        read_bundle_verification_response(raw)


def test_response_reader_rejects_missing_duplicate_deep_invalid_and_large_records():
    missing = {k: v for k, v in VALID.items() if k != "identity_checked"}
    duplicate = json.dumps(VALID).replace('"verified": true', '"verified": true, "verified": true')
    for raw in (
        json.dumps(missing).encode(),
        duplicate.encode(),
        b"[" * 1500 + b"]" * 1500,
        b"\xff",
    ):
        with pytest.raises(ValueError, match="^invalid bundle verification response$"):
            read_bundle_verification_response(raw)
    with pytest.raises(ValueError, match="^verification response exceeds byte limit$"):
        read_bundle_verification_response(b" " * (MAX_VERIFICATION_RESPONSE_BYTES + 1))


def test_verification_check_validates_shape_without_repeating_claims(tmp_path, capsys):
    path = tmp_path / "response.json"
    raw = json.dumps({**VALID, "source_checked": True, "identity_checked": True}).encode()
    path.write_bytes(raw)
    assert main(["sweep-bundle-verification-check", str(path)]) == 0
    output = capsys.readouterr()
    assert not output.err
    assert json.loads(output.out) == {
        "schema_version": 1,
        "valid": True,
        "interpretation": "verification_response_validity_only",
    }
    assert path.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [path]


def test_verification_check_rejects_bad_records_without_echo(tmp_path, capsys):
    path = tmp_path / "response.json"
    duplicate = json.dumps(VALID).replace('"verified": true', '"verified": true, "verified": true')
    for raw in (
        duplicate.encode(),
        json.dumps({**VALID, "interpretation": "synthetic_private_value"}).encode(),
        b" " * MAX_VERIFICATION_RESPONSE_BYTES + json.dumps(VALID).encode(),
    ):
        path.write_bytes(raw)
        assert main(["sweep-bundle-verification-check", str(path)]) == 2
        output = capsys.readouterr()
        assert not output.out
        assert "synthetic_private_value" not in output.err
        assert str(path) not in output.err
        assert path.read_bytes() == raw


def test_verify_exports_emits_a_receipt_only_after_both_exports_match(tmp_path, capsys):
    before, after = source(), source(seeds=[9])
    bundle = create_bundle(before, after)
    bundle_path = tmp_path / "bundle.json"
    html_path = tmp_path / "review.html"
    csv_path = tmp_path / "review.csv"
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    bundle_path.write_bytes(encode_bundle(bundle))
    html_path.write_bytes(render_plan_diff(before, after, schema_version=2).encode())
    csv_path.write_bytes(render_plan_diff_csv(before, after).encode())
    before_path.write_text(before.model_dump_json(), encoding="utf-8")
    after_path.write_text(after.model_dump_json(), encoding="utf-8")
    inputs = {
        path: path.read_bytes()
        for path in (bundle_path, html_path, csv_path, before_path, after_path)
    }
    args = list(map(str, ["sweep-bundle-verify-exports", bundle_path, html_path, csv_path]))
    sources = list(map(str, ["--before", before_path, "--after", after_path]))
    digest = bundle_identity(bundle)["bundle_sha256"]
    assert main(args) == 0
    receipt = read_bundle_verification_response(capsys.readouterr().out.encode())
    assert receipt.verified and not receipt.source_checked and not receipt.identity_checked

    checked = args + sources + ["--expected-sha256", digest]
    assert main(checked) == 0
    receipt = read_bundle_verification_response(capsys.readouterr().out.encode())
    assert receipt.source_checked and receipt.identity_checked
    assert {path: path.read_bytes() for path in inputs} == inputs

    for path in (html_path, csv_path):
        edited = inputs[path] + b"synthetic_private_value"
        path.write_bytes(edited)
        assert main(checked) == 2
        result = capsys.readouterr()
        assert not result.out
        assert "synthetic_private_value" not in result.err
        assert str(path) not in result.err
        assert path.read_bytes() == edited
        path.write_bytes(inputs[path])

    assert main(args + sources[:2]) == 2
    assert not capsys.readouterr().out
    assert main(args + ["--expected-sha256", "0" * 64]) == 2
    assert not capsys.readouterr().out
    assert {path: path.read_bytes() for path in inputs} == inputs


def test_export_pair_diagnostics_identify_only_first_failed_stage(tmp_path, capsys):
    before, after = source(), source(seeds=[9])
    bundle = create_bundle(before, after)
    paths = {name: tmp_path / f"synthetic_private_{name}" for name in ("bundle", "html", "csv")}
    original = {
        "bundle": encode_bundle(bundle),
        "html": render_plan_diff(before, after, schema_version=2).encode(),
        "csv": render_plan_diff_csv(before, after).encode(),
    }
    for name, path in paths.items():
        path.write_bytes(original[name])
    args = [str(p) for p in ["sweep-bundle-verify-exports", *paths.values(), "--diagnostics"]]

    def expect_failure(stage, extra=()):
        assert main(args + list(extra)) == 2
        result = capsys.readouterr()
        assert not result.out
        assert json.loads(result.err) == {
            "schema_version": 1,
            "error": "verification_failed",
            "stage": stage,
        }
        assert "synthetic_private" not in result.err

    assert main(args) == 0
    result = capsys.readouterr()
    assert not result.err
    assert read_bundle_verification_response(result.out.encode()).verified
    expect_failure("identity", ["--expected-sha256", "0" * 64])
    expect_failure("sources", ["--before", str(paths["bundle"])])

    for stage, path in paths.items():
        path.write_bytes(b"synthetic_private_value")
        expect_failure(stage)
        assert path.read_bytes() == b"synthetic_private_value"
        path.write_bytes(original[stage])

    paths["html"].write_bytes(b"synthetic_private_value")
    paths["csv"].unlink()
    expect_failure("html")
    paths["html"].write_bytes(original["html"])
    expect_failure("csv")
