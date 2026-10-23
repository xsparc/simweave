"""Offline rendering preserves review semantics and escapes source text."""

import base64
import hashlib
from html.parser import HTMLParser

import pytest

from simweave.cli import main
from simweave.suites import SuiteReport, execute_suite
from simweave.sweep_html import STYLE, render_sweep_report
from simweave.sweep_review import summarize
from simweave.sweeps import Sweep, plan


@pytest.fixture
def evidence(tmp_path):
    source = Sweep.model_validate(
        {
            "name": '</title><script>alert("x")</script>&',
            "scenario": {"world": {"steps": 10}},
            "axes": [{"field": "robot.mass", "values": [1.0, 2.0]}],
            "seeds": [8, 3],
            "adapters": ["reference"],
            "baseline": {},
            "candidate": {"kp": 9.0},
        }
    )
    return source, execute_suite(plan(source), tmp_path / "bundle")


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)


def test_escaped_static_document_and_matching_evidence(evidence):
    source, report = evidence
    output, code = render_sweep_report(source, report)
    assert (output, code) == render_sweep_report(source, report)
    assert code == 1
    parser = Tags()
    parser.feed(output)
    assert not set(parser.tags) & {"script", "iframe", "img", "a", "form", "link"}
    assert not any(name.startswith("on") for name, _ in parser.attributes)
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;&amp;" in output
    policy = next(value for name, value in parser.attributes if name == "content")
    digest = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    assert f"style-src 'sha256-{digest}'" in policy
    assert "script-src 'none'" in policy
    assert parser.tags.count("table") == 2
    result = summarize(source, report)
    assert result.report_digest in output and result.sweep_digest in output
    assert "Seeds:</strong> 8, 3" in output
    for point in result.points:
        for metric in point.metrics:
            assert f"<td>{metric.delta_mean:.6g}</td>" in output


def test_incomplete_point_withholds_metrics(evidence):
    source, report = evidence
    data = report.model_dump()
    data["cases"][0].update(summary=None, error="execution_failed")
    output, code = render_sweep_report(source, SuiteReport.model_validate(data))
    assert code == 2
    assert "Incomplete execution" in output
    assert "Metrics withheld: incomplete seed pairs." in output
    assert output.count("<table>") == 1


def test_cli_exclusive_output_and_validation_before_write(evidence, tmp_path, capsys):
    source, report = evidence
    source_path, report_path = tmp_path / "sweep.json", tmp_path / "report.json"
    source_path.write_text(source.model_dump_json(), encoding="utf-8")
    report_path.write_text(report.model_dump_json(), encoding="utf-8")
    args = ["sweep-review", str(source_path), str(report_path), "--format", "html"]
    assert main(args) == 1
    expected = capsys.readouterr().out
    assert expected.startswith("<!doctype html>")
    output = tmp_path / "report.html"
    assert main(args + ["--output", str(output)]) == 1
    assert output.read_text(encoding="utf-8").strip() == expected.strip()
    original = output.read_bytes()
    assert main(args + ["--output", str(output)]) == 2
    assert output.read_bytes() == original
    report = report.model_copy(update={"suite_digest": "0" * 64})
    report_path.write_text(report.model_dump_json(), encoding="utf-8")
    rejected = tmp_path / "rejected.html"
    assert main(args + ["--output", str(rejected)]) == 2
    assert not rejected.exists()
