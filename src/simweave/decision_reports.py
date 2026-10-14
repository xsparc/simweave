"""Script-free portable decision reports; all evidence text is escaped."""

import base64
import hashlib
import html
import json
from pathlib import Path

from simweave.statistics import StatisticalReport

STYLE = """
:root{color-scheme:light;font:16px/1.55 system-ui,sans-serif;color:#192f2a;background:#f4f3eb}
*{box-sizing:border-box}body{max-width:1120px;margin:0 auto;padding:40px 24px 70px}
header{border-bottom:1px solid #b9c6bb;padding-bottom:28px;margin-bottom:30px}
.brand{letter-spacing:.16em;font-size:12px;text-transform:uppercase;font-weight:750;color:#426453}
h1{font-size:clamp(30px,4vw,48px);letter-spacing:-.04em;line-height:1.15;margin:16px 0}
h2{font-size:23px;margin:0 0 12px}p{margin:10px 0}.muted{color:#53665d}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin:24px 0}
.card,section{background:#fffefa;border:1px solid #c9d1c4;border-radius:14px;padding:24px}
.card strong{display:block;font-size:29px;font-weight:650;line-height:1.2;margin-top:8px}
section{margin:20px 0}.badge{display:inline-block;padding:4px 12px;border-radius:20px;
font-weight:650;font-size:14px;background:#e5e9dd}.regression{color:#9e2727;background:#fde8df}
.within_tolerance{color:#155443;background:#e0f0e7}.inconclusive{color:#704b06;background:#fbefc9}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:13px 10px;text-align:left;border-bottom:1px solid #dce1d7;vertical-align:top}
th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#53665d}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}code{overflow-wrap:anywhere}
summary{cursor:pointer;font-weight:650}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}
a{color:#155443}li{margin:6px 0}.note{border-left:3px solid #c89636;padding-left:15px}
footer{margin-top:28px;font-size:13px;color:#53665d}
@media print{body{padding:0;background:white}section{break-inside:avoid}details{display:none}}
"""


def escape(value) -> str:
    return html.escape(str(value), quote=True)


def _page(title: str, content: str) -> str:
    sha = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    policy = (
        "default-src 'none'; base-uri 'none'; form-action 'none'; "
        f"style-src 'sha256-{sha}'; script-src 'none'; object-src 'none'"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{escape(policy)}">'
        f"<title>{escape(title)} · SimWeave</title><style>{STYLE}</style></head><body>"
        '<header><div class="brand">SimWeave / regression decisions</div>'
        f"<h1>{escape(title)}</h1>"
        '<p class="muted">Recorded evidence. Explicit tolerances. Reviewable decisions.</p>'
        f"</header><main>{content}</main>"
        "<footer>Portable offline report · No scripts, API, or external assets. "
        "Checksums and approval labels are unsigned assertions.</footer></body></html>"
    )


def _badge(status: str) -> str:
    return f'<span class="badge {escape(status)}">{escape(status.replace("_", " "))}</span>'


def render_statistics(report: StatisticalReport, context: dict | None = None) -> str:
    content = _badge(report.status)
    content += '<div class="grid">'
    for label, value in (
        ("Complete paired seeds", sum(g.complete_pairs for g in report.groups)),
        ("Bootstrap resamples", f"{report.policy.resamples:,}"),
        ("Marginal confidence", "95%"),
    ):
        content += f'<div class="card">{label}<strong>{value}</strong></div>'
    content += '</div><p class="note">Intervals describe the mean paired change, '
    content += "candidate minus baseline. Positive changes are worse for the selected metrics. "
    content += "Review quality failures and uncertainty before approving a build.</p>"
    if context:
        content += "<section><h2>Pinned baseline</h2><p>"
        content += f"{escape(context['baseline_build'])} → {escape(context['candidate_build'])}"
        content += f" · approval generation {escape(context['baseline_generation'])}</p>"
        content += (
            f'<p class="muted">Policy SHA-256: <code>{report.policy_digest}</code></p></section>'
        )
    for group in report.groups:
        content += f"<section><h2>{escape(group.name)} · {escape(group.adapter)}</h2>"
        content += (
            f'<p class="muted">{group.complete_pairs} complete pairs / {len(group.seeds)} seeds · '
            f"{group.quality_failures} quality failures · "
            f"{group.individual_regression_failures} individual regression failures</p>"
        )
        for issue in group.issues:
            content += f'<p class="note">{escape(issue)}</p>'
        content += '<div class="scroll"><table><thead><tr><th>Metric</th><th>Mean change</th>'
        content += (
            "<th>95% interval</th><th>Allowed increase</th><th>Decision</th></tr></thead><tbody>"
        )
        for metric in group.metrics:
            interval = metric.interval
            mean = f"{interval.mean:+.6g}" if interval else "Unavailable"
            bounds = f"[{interval.low:+.6g}, {interval.high:+.6g}]" if interval else "Unavailable"
            if interval and interval.constant:
                bounds += " (constant)"
            content += (
                f'<tr><td>{escape(metric.metric)}</td><td class="num">{mean}</td>'
                f'<td class="num">{bounds}</td><td class="num">{metric.max_increase:.6g}</td>'
                f"<td>{_badge(metric.verdict)}</td></tr>"
            )
        content += "</tbody></table></div></section>"
    content += "<section><h2>Interpretation &amp; limitations</h2><ul>"
    content += "".join(f"<li>{escape(w)}</li>" for w in report.warnings)
    content += "</ul><p>Minimum 30 pairs per scenario / adapter. "
    content += (
        f"Algorithm: <code>{report.algorithm}</code>; random seed {report.policy.random_seed}.</p>"
    )
    content += '<p><a href="decision.json">Open versioned JSON</a></p></section>'
    return _page("Regression decision", content)


def write_statistics(report: StatisticalReport, output: Path, context: dict | None = None):
    output.mkdir(parents=True, exist_ok=False)
    data = context or report.model_dump()
    (output / "decision.json").write_text(
        json.dumps(data, indent=2, allow_nan=False), encoding="utf-8"
    )
    (output / "report.html").write_text(render_statistics(report, context), encoding="utf-8")


def write_history(data: dict, output: Path):
    output.mkdir(parents=True, exist_ok=False)
    content = '<div class="grid">'
    for label, value in (
        ("Approved baseline", data["active_baseline"] or "None"),
        ("Approval generation", data["generation"]),
        ("Recorded comparisons", len(data["comparisons"])),
    ):
        content += f'<div class="card">{label}<strong>{escape(value)}</strong></div>'
    content += '</div><section><h2>Approval history</h2><div class="scroll"><table>'
    content += "<thead><tr><th>Generation</th><th>Action / build</th>"
    content += "<th>Approval</th><th>Reason</th></tr></thead><tbody>"
    for event in reversed(data["events"]):
        restored = (
            f" (restores {event['restored_generation']})" if event["restored_generation"] else ""
        )
        content += (
            f"<tr><td>{event['generation']}</td><td>{escape(event['action'])}{restored}<br>"
            f"{escape(event['build'])}</td><td>{escape(event['approval']['approved_by'])}<br>"
            f"{escape(event['recorded_at'])}</td><td>{escape(event['approval']['reason'])}</td></tr>"
        )
    content += "</tbody></table></div></section><section><h2>Candidate decisions</h2>"
    content += '<div class="scroll"><table><thead><tr><th>Candidate</th><th>Pinned baseline</th>'
    content += "<th>Generation</th><th>Decision</th></tr></thead><tbody>"
    for comparison in reversed(data["comparisons"]):
        content += (
            f"<tr><td>{escape(comparison['candidate_build'])}</td>"
            f"<td>{escape(comparison['baseline_build'])}</td>"
            f"<td>{comparison['baseline_generation']}</td>"
            f"<td>{_badge(comparison['statistics']['status'])}</td></tr>"
        )
    content += (
        '</tbody></table></div><p><a href="history.json">Open full JSON history</a></p></section>'
    )
    content += '<p class="note">Original evidence bundles must be retained separately. '
    content += "This local catalog is not an authenticated approval service.</p>"
    (output / "history.json").write_text(
        json.dumps(data, indent=2, allow_nan=False), encoding="utf-8"
    )
    (output / "report.html").write_text(_page("Baseline history", content), encoding="utf-8")
