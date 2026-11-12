import json
import runpy
from pathlib import Path

import pytest
from test_sweep_diff import source

from simweave.bundle_identity import bundle_identity
from simweave.cli import main
from simweave.plan_bundle import MAX_COMPONENT, create_bundle, encode_bundle, verify_bundle_html
from simweave.sweep_diff import render_plan_diff, render_plan_diff_csv


def test_exact_html_and_bounds():
    bundle = create_bundle(source(), source(seeds=[9]))
    html = render_plan_diff(bundle.before, bundle.after, schema_version=2).encode()
    verify_bundle_html(bundle, html)
    for changed in [
        html + b"\n",
        html.replace(b"style", b"STYLE"),
        html.replace(b"Content-Security-Policy", b"Removed-Security-Policy"),
        html.replace(b"<", b"[", 1),
        b"\xff",
        b"x" * (MAX_COMPONENT + 1),
    ]:
        with pytest.raises(ValueError):
            verify_bundle_html(bundle, changed)


@pytest.mark.parametrize("format", ["html", "csv"])
def test_cli_gates_and_read_only(tmp_path, monkeypatch, capsys, format):
    monkeypatch.setattr("simweave.suites.execute", lambda *a, **k: pytest.fail("execution"))
    render = (
        (lambda a, b: render_plan_diff(a, b, schema_version=2))
        if format == "html"
        else render_plan_diff_csv
    )
    a, b = source(), source(seeds=[9])
    bundle = create_bundle(a, b)
    left, right, retained, identity, html = [
        tmp_path / n for n in ("a.json", "b.json", "bundle.json", "id.json", "review.html")
    ]
    left.write_text(a.model_dump_json())
    right.write_text(b.model_dump_json())
    retained.write_bytes(encode_bundle(bundle))
    identity.write_text(json.dumps(bundle_identity(bundle)))
    html.write_bytes(render(a, b).encode())
    saved = {p: p.read_bytes() for p in (left, right, retained, identity, html)}
    base = ["sweep-bundle-verify-" + format, str(retained), str(html)]
    sources = ["--before", str(left), "--after", str(right)]
    assert main(base) == 0
    assert main(base + sources + ["--identity", str(identity)]) == 0
    assert main(base + sources + ["--expected-sha256", "0" * 64]) == 2
    assert main(base + ["--before", str(left)]) == 2
    assert main(base + ["--before", str(right), "--after", str(left)]) == 2
    replacement = create_bundle(a, a)
    retained.write_bytes(encode_bundle(replacement))
    identity.write_text(json.dumps(bundle_identity(replacement)))
    html.write_bytes(render(a, a).encode())
    assert main(base + ["--identity", str(identity)]) == 0
    assert main(base + sources + ["--identity", str(identity)]) == 2
    for p, raw in saved.items():
        p.write_bytes(raw)
    html.write_bytes(b"x" * (MAX_COMPONENT + 1))
    assert main(base) == 2
    html.write_bytes(saved[html])
    assert all(p.read_bytes() == raw for p, raw in saved.items())
    assert str(tmp_path) not in capsys.readouterr().err


def test_executable_portable_review(tmp_path):
    example = runpy.run_path(str(Path("examples/portable_review.py")))
    assert example["run"](tmp_path / "review") == {
        "verified": True,
        "formats": ["html", "csv"],
        "simulation": "none",
    }
