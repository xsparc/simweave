import csv
import io
import json
from pathlib import Path

import pytest
from test_sweep_diff import source

from simweave.cli import main
from simweave.sweep_diff import render_plan_diff, render_plan_diff_csv, verify_plan_diff_csv


@pytest.mark.parametrize(
    "mutation", ["cell", "header", "order", "extra", "missing", "newline", "utf8", "size"]
)
def test_csv_rejects_changed_contract(mutation):
    before, after = source(), source(adapters=["mujoco"])
    raw = render_plan_diff_csv(before, after).encode()
    assert verify_plan_diff_csv(before, after, raw).schema_version == 2
    rows = list(csv.reader(io.StringIO(raw.decode(), newline="")))
    if mutation == "cell":
        rows[1][6] = "999"
    elif mutation == "header":
        rows[0][0] = "unexpected"
    elif mutation == "order":
        rows[2:] = reversed(rows[2:])
    elif mutation == "extra":
        rows.append(rows[-1])
    elif mutation == "missing":
        rows.pop()
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerows(rows)
    changed = stream.getvalue().encode()
    if mutation == "newline":
        changed = raw.replace(b"\r\n", b"\n")
    elif mutation == "utf8":
        changed = b"\xff"
    elif mutation == "size":
        changed = b" " * 65537
    with pytest.raises(ValueError):
        verify_plan_diff_csv(before, after, changed)
    with pytest.raises(ValueError):
        verify_plan_diff_csv(after, before, raw)


def test_v2_html_escapes_labels_and_preserves_v1():
    before, after = source(name="<script>alert(1)</script>"), source(adapters=["mujoco"])
    legacy = render_plan_diff(before, after)
    assert legacy == render_plan_diff(before, after, schema_version=1)
    html = render_plan_diff(before, after, schema_version=2)
    assert "<script" not in html and "&lt;script&gt;" in html
    assert "Adapter counts" in html and "Adapter counts" not in legacy
    assert "default-src" in html and "sha256-" in html
    assert "table-wrap" in html and "+4" in html and "-4" in html


def test_portable_example_all_transports_without_execution(tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("plan review must not execute a simulator")

    monkeypatch.setattr("simweave.suites.execute", forbidden)
    root = Path(__file__).resolve().parents[1] / "examples" / "plan-review"
    sources = [root / "before.json", root / "after.json"]
    original = [p.read_bytes() for p in sources]
    for version in (1, 2):
        target = tmp_path / f"v{version}.json"
        assert (
            main(
                [
                    "sweep-diff",
                    *map(str, sources),
                    "--schema-version",
                    str(version),
                    "--output",
                    str(target),
                ]
            )
            == 0
        )
        data = json.loads(target.read_bytes())
        assert data["runs_delta"] == data["steps_delta"] == 0
        assert not data["identical_inputs"]
        assert data["added_adapters"] == ["mujoco"] and data["removed_adapters"] == ["gazebo"]
        assert main(["sweep-diff-verify", *map(str, sources), str(target)]) == 0
        html = tmp_path / f"v{version}.html"
        assert (
            main(
                [
                    "sweep-diff",
                    *map(str, sources),
                    "--format",
                    "html",
                    "--schema-version",
                    str(version),
                    "--output",
                    str(html),
                ]
            )
            == 0
        )
        assert ("Adapter counts" in html.read_text("utf-8")) == (version == 2)
    target = tmp_path / "review.csv"
    assert main(["sweep-diff", *map(str, sources), "--format", "csv", "--output", str(target)]) == 0
    args = ["sweep-diff-verify", *map(str, sources), str(target), "--format", "csv"]
    assert main(args) == 0
    capsys.readouterr()
    assert (
        main(["sweep-diff-verify", *map(str, reversed(sources)), str(target), "--format", "csv"])
        == 2
    )
    assert not capsys.readouterr().out
    target.write_bytes(target.read_bytes() + b"\r\n")
    assert main(args) == 2
    assert [p.read_bytes() for p in sources] == original
