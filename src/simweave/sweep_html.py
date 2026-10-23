"""Offline sweep review: escaped text, fixed CSS, no scripts or external assets."""

import base64
import hashlib
from html import escape

from simweave.suites import SuiteReport
from simweave.sweep_review import summarize
from simweave.sweeps import Sweep

STYLE = """
:root { color-scheme: light; font-family: system-ui, sans-serif; color: #183044;
background: #f3f6f8; line-height: 1.55; }
body { margin: 0; } main { max-width: 1100px; margin: auto; padding: 2rem; }
h1 { font-size: 2.4rem; margin: .3rem 0; } h2 { margin-top: 0; }
.eyebrow { color: #486579; text-transform: uppercase; letter-spacing: .12em; }
.cards { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1.5rem 0; }
.card, section { background: white; border: 1px solid #cdd9e0; border-radius: .7rem;
padding: 1.2rem; } .card { flex: 1; min-width: 8rem; }
.card strong { display: block; font-size: 1.7rem; }
section { margin: 1rem 0; } .pass { color: #176348; }
.fail { color: #973523; } .incomplete { color: #855000; }
.notice { border-left: 4px solid #9b6718; padding-left: 1rem; }
.table-wrap { overflow-x: auto; } table { border-collapse: collapse; width: 100%; }
th, td { text-align: right; padding: .7rem; border-bottom: 1px solid #dbe3e8; }
th:first-child, td:first-child { text-align: left; }
caption { text-align: left; font-weight: 600; margin: .5rem 0; }
code { overflow-wrap: anywhere; } dt { font-weight: 600; } dd { margin: 0 0 1rem; }
@media print { :root { background: white; } main { padding: 0; }
section { break-inside: avoid; } .table-wrap { overflow: visible; } }
"""


def render_sweep_report(sweep: Sweep, report: SuiteReport) -> tuple[str, int]:
    """Recompute from validated source contracts; never render an imported summary."""
    result = summarize(sweep, report)
    status = ("Passed", "Quality or regression failures", "Incomplete execution")[result.exit_code]
    status_class = ("pass", "fail", "incomplete")[result.exit_code]
    digest = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    policy = (
        "default-src 'none'; base-uri 'none'; form-action 'none'; "
        f"style-src 'sha256-{digest}'; script-src 'none'; connect-src 'none'; "
        "img-src 'none'; object-src 'none'"
    )
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{escape(policy, quote=True)}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Sweep review: {escape(sweep.name)}</title><style>{STYLE}</style></head>",
        '<body><main><header><p class="eyebrow">SimWeave / Sweep evidence</p>',
        f'<h1>{escape(sweep.name)}</h1><p class="{status_class}">{status}</p></header>',
        '<div class="cards">',
    ]
    for label, count in (
        ("Parameter / adapter points", len(result.points)),
        ("Passed pairs", sum(p.passed_pairs for p in result.points)),
        ("Failed pairs", sum(p.failed_pairs for p in result.points)),
        ("Execution-error pairs", sum(p.error_pairs for p in result.points)),
    ):
        parts.append(f'<div class="card"><strong>{count}</strong>{label}</div>')
    parts.append(
        '</div><p class="notice">Descriptive results only. No confidence intervals, '
        "optimal-controller selection or baseline approval is implied. Positive deltas mean "
        "larger values; gate definitions determine failure. Values display six significant "
        "digits; use JSON for full precision.</p>"
    )
    for index, point in enumerate(result.points, 1):
        parts.append(f'<section aria-labelledby="point-{index}">')
        parts.append(
            f'<h2 id="point-{index}">{escape(point.scenario)} / {escape(point.adapter)}</h2>'
        )
        parameters = "; ".join(f"{key} = {value:.6g}" for key, value in point.parameters.items())
        parts.append(f"<p><strong>Parameters:</strong> {escape(parameters)}</p>")
        parts.append(f"<p><strong>Seeds:</strong> {', '.join(map(str, point.seeds))}</p>")
        parts.append(
            f"<p>Passed: {point.passed_pairs} · Failed: {point.failed_pairs} · "
            f"Execution errors: {point.error_pairs}</p>"
        )
        for warning in point.warnings:
            parts.append(f'<p class="notice">{escape(warning)}</p>')
        if point.metrics is None:
            parts.append(
                '<p class="incomplete"><strong>Metrics withheld: '
                "incomplete seed pairs.</strong></p>"
            )
        else:
            parts.append(
                '<div class="table-wrap"><table><caption>Metrics across all listed seeds</caption>'
                '<thead><tr><th scope="col">Metric</th><th scope="col">Baseline mean</th>'
                '<th scope="col">Candidate mean</th><th scope="col">Delta mean</th>'
                '<th scope="col">Delta minimum</th><th scope="col">Delta maximum</th>'
                "</tr></thead><tbody>"
            )
            for metric in point.metrics:
                parts.append(f'<tr><th scope="row">{escape(metric.metric)}</th>')
                for value in (
                    metric.baseline_mean,
                    metric.candidate_mean,
                    metric.delta_mean,
                    metric.delta_min,
                    metric.delta_max,
                ):
                    parts.append(f"<td>{value:.6g}</td>")
                parts.append("</tr>")
            parts.append("</tbody></table></div>")
        parts.append("</section>")
    parts.append('<section aria-labelledby="identity"><h2 id="identity">Evidence identity</h2><dl>')
    for label, value in (
        ("Suite", result.suite_digest),
        ("Sweep", result.sweep_digest),
        ("Source report", result.report_digest),
    ):
        parts.append(f"<dt>{label} SHA-256</dt><dd><code>{value}</code></dd>")
    parts.append(
        "</dl><p>Hashes bind normalized source contracts. This report validates summaries, "
        "not full telemetry, signatures or physical accuracy. Use bundle verification and "
        "the provenance workflow for additional evidence.</p></section></main></body></html>"
    )
    return "".join(parts), result.exit_code
