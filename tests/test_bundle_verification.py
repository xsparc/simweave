import json
from pathlib import Path

import pytest
from test_sweep_diff import source

from simweave.cli import main
from simweave.plan_bundle import (
    create_bundle,
    encode_bundle,
    read_bundle,
    verify_bundle_csv,
    verify_bundle_sources,
)
from simweave.sweep_diff import render_plan_diff_csv


def test_external_sources_reject_consistent_replacement_and_direction(monkeypatch):
    monkeypatch.setattr("simweave.suites.execute", lambda *a, **k: pytest.fail("execution"))
    before, after = source(), source(seeds=[2])
    raw = encode_bundle(create_bundle(before, after))
    assert verify_bundle_sources(raw, before, after) == read_bundle(raw)
    assert verify_bundle_sources(json.dumps(json.loads(raw), indent=4).encode(), before, after)
    for left, right in [(after, before), (before, before), (after, after)]:
        replacement = encode_bundle(create_bundle(left, right))
        assert read_bundle(replacement)
        with pytest.raises(ValueError):
            verify_bundle_sources(replacement, before, after)
    assert read_bundle(raw).comparison.runs_delta == 0


@pytest.mark.parametrize("mutation", ["lf", "prefix", "order", "utf8", "extra"])
def test_bundle_csv_exact_bytes(mutation):
    bundle = create_bundle(source(name="=formula"), source(seeds=[2]))
    raw = render_plan_diff_csv(bundle.before, bundle.after).encode()
    verify_bundle_csv(bundle, raw)
    if mutation == "lf":
        raw = raw.replace(b"\r\n", b"\n")
    elif mutation == "prefix":
        raw = raw.replace(b"text:", b"")
    elif mutation == "order":
        raw = b"\r\n".join(reversed(raw.split(b"\r\n")))
    elif mutation == "utf8":
        raw += b"\xff"
    else:
        raw += b"\r\n"
    with pytest.raises(ValueError):
        verify_bundle_csv(bundle, raw)


def test_portable_cli_both_verifiers_read_only(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("simweave.suites.execute", lambda *a, **k: pytest.fail("execution"))
    before, after = sorted(Path("examples/plan-review").glob("*.json"))
    bundle, csv = tmp_path / "bundle.json", tmp_path / "review.csv"
    assert main(["sweep-bundle", str(before), str(after), "--output", str(bundle)]) == 0
    assert main(["sweep-bundle-render", str(bundle), "--format", "csv", "--output", str(csv)]) == 0
    args = ["sweep-bundle-verify-sources", str(bundle), str(before), str(after)]
    csv_args = ["sweep-bundle-verify-csv", str(bundle), str(csv)]
    snapshot = {p: p.read_bytes() for p in [before, after, bundle, csv]}
    assert main(args) == main(csv_args) == 0
    assert all(p.read_bytes() == raw for p, raw in snapshot.items())
    assert main([args[0], str(bundle), str(after), str(before)]) == 2
    oversized = tmp_path / "large.json"
    oversized.write_bytes(b" " * (65536 + 1))
    assert main([args[0], str(bundle), str(oversized), str(after)]) == 2
    assert main([csv_args[0], str(bundle), str(oversized)]) == 2
    assert str(tmp_path) not in capsys.readouterr().err
    checked = read_bundle(bundle.read_bytes())
    checked.before.seeds.append(99)
    with pytest.raises(ValueError):
        verify_bundle_csv(checked, csv.read_bytes())
