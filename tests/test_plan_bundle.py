import json
from pathlib import Path

import pytest
from test_sweep_diff import source

from simweave.cli import main
from simweave.plan_bundle import MAX_BUNDLE, create_bundle, encode_bundle, read_bundle
from simweave.sweep_diff import compare_plans, render_plan_diff, render_plan_diff_csv


@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("bundle verification must not execute simulation")

    monkeypatch.setattr("simweave.suites.execute", forbidden)


def test_canonical_roundtrip_and_existing_renderers():
    before, after = source(name="<script>alert(1)</script>"), source(adapters=["mujoco"])
    bundle = create_bundle(before, after)
    raw = encode_bundle(bundle)
    assert raw == encode_bundle(create_bundle(before, after))
    assert raw.endswith(b"\n") and read_bundle(raw) == bundle
    assert read_bundle(json.dumps(json.loads(raw), indent=2).encode()) == bundle
    assert bundle.comparison == compare_plans(before, after, schema_version=2)
    html = render_plan_diff(bundle.before, bundle.after, schema_version=2)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert render_plan_diff_csv(bundle.before, bundle.after) == render_plan_diff_csv(before, after)
    inverse = create_bundle(after, before)
    assert inverse.comparison.runs_delta == -bundle.comparison.runs_delta
    assert inverse.comparison.before == bundle.comparison.after


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "boolean",
        "missing",
        "extra",
        "source",
        "digest",
        "direction",
        "report",
        "budget",
        "nested-extra",
        "comparison-version",
    ],
)
def test_reject_inconsistent_envelopes(mutation):
    data = json.loads(encode_bundle(create_bundle(source(), source(seeds=[2]))))
    if mutation == "version":
        data["schema_version"] = 2
    elif mutation == "boolean":
        data["schema_version"] = True
    elif mutation == "missing":
        del data["schema_version"]
    elif mutation == "extra":
        data["path"] = "https://invalid.example/asset"
    elif mutation == "source":
        data["before"]["seeds"] = [3]
    elif mutation == "digest":
        data["comparison"]["before"]["sweep_digest"] = "0" * 64
    elif mutation == "direction":
        data["before"], data["after"] = data["after"], data["before"]
    elif mutation == "report":
        data["comparison"]["runs_delta"] = 1
    elif mutation == "budget":
        data["before"]["seeds"] = list(range(32))
    elif mutation == "nested-extra":
        data["before"]["scenario"]["path"] = "private-value"
    elif mutation == "comparison-version":
        data["comparison"]["schema_version"] = 1
    with pytest.raises(ValueError):
        read_bundle(json.dumps(data).encode())


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff",
        b"{}",
        b"[]",
        b" " * (MAX_BUNDLE + 1),
        b'{"schema_version":1,"schema_version":1}',
        b"[" * 2000 + b"]" * 2000,
    ],
    ids=["utf8", "empty-object", "array", "size", "duplicate", "depth"],
)
def test_reject_invalid_and_ambiguous_input(raw):
    with pytest.raises(ValueError):
        read_bundle(raw)


def test_revalidate_mutated_models():
    bundle = create_bundle(source(), source(seeds=[2]))
    bundle.before.seeds.append(3)
    with pytest.raises(ValueError):
        encode_bundle(bundle)
    before = source()
    before.adapters.append("unregistered")
    with pytest.raises(ValueError):
        create_bundle(before, source())


def test_cli_retained_fixture_and_failure_atomicity(tmp_path, capsys):
    examples = Path("examples/plan-review")
    files = sorted(examples.glob("*.json"))
    assert len(files) == 2
    original = [p.read_bytes() for p in files]
    target = tmp_path / "bundle.json"
    args = ["sweep-bundle", *map(str, files), "--output", str(target)]
    assert main(args) == 0
    original_bundle = target.read_bytes()
    assert main(args) == 2 and target.read_bytes() == original_bundle
    assert main(["sweep-bundle-verify", str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["interpretation"] == "local_source_consistency_only"
    for format in ("html", "csv"):
        output = tmp_path / ("review." + format)
        render = ["sweep-bundle-render", str(target), "--format", format, "--output", str(output)]
        assert main(render) == 0
        assert main(render) == 2
        bundle = read_bundle(original_bundle)
        expected = (
            render_plan_diff(bundle.before, bundle.after, schema_version=2)
            if format == "html"
            else render_plan_diff_csv(bundle.before, bundle.after)
        )
        assert output.read_bytes() == expected.encode("utf-8")
    data = json.loads(original_bundle)
    data["before"]["name"] = "private-fixture-marker"
    target.write_text(json.dumps(data))
    missing = tmp_path / "rejected.html"
    capsys.readouterr()
    assert main(["sweep-bundle-render", str(target), "--output", str(missing)]) == 2
    result = capsys.readouterr()
    assert not result.out and "private-fixture-marker" not in result.err and not missing.exists()
    assert [p.read_bytes() for p in files] == original
    target.write_bytes(b" " * (MAX_BUNDLE + 1))
    assert main(["sweep-bundle-verify", str(target)]) == 2
    assert main(["sweep-bundle-schema"]) == 0
    assert json.loads(capsys.readouterr().out)["additionalProperties"] is False


@pytest.mark.parametrize("kind", ["duplicate", "depth", "size"])
def test_cli_source_intake_rejects_before_output(tmp_path, capsys, kind):
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    after.write_text(source().model_dump_json())
    bad = {
        "duplicate": b'{"schema_version":1,"schema_version":1}',
        "depth": b"[" * 2000 + b"]" * 2000,
        "size": b" " * 65537,
    }[kind]
    before.write_bytes(bad)
    target = tmp_path / "absent.json"
    assert main(["sweep-bundle", str(before), str(after), "--output", str(target)]) == 2
    result = capsys.readouterr()
    assert not target.exists() and not result.out
    assert "Operation failed" in result.err and "Traceback" not in result.err
    assert before.read_bytes() == bad


def test_normalized_component_bound(monkeypatch):
    import simweave.plan_bundle as module

    bundle = create_bundle(source(), source(seeds=[2]))
    monkeypatch.setattr(module, "MAX_COMPONENT", 1)
    with pytest.raises(ValueError):
        read_bundle(json.dumps(bundle.model_dump()).encode())
