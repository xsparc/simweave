"""Render a self-contained review with no server, network, or external assets."""

import base64
import hashlib
import json
from importlib.resources import files
from pathlib import Path

from simweave.provenance import Environment
from simweave.suites import SuiteReport, review


def render_report(report: SuiteReport, environment: Environment | None = None) -> str:
    assets = files("simweave").joinpath("static")
    script = assets.joinpath("offline.js").read_text(encoding="utf-8")
    style = assets.joinpath("offline.css").read_text(encoding="utf-8")
    data = (
        json.dumps(
            {
                "review": review(report).model_dump(),
                "suite": report.suite.model_dump(),
                "environment": environment.model_dump() if environment else None,
            },
            ensure_ascii=True,
            allow_nan=False,
        )
        .replace("<", "\\u003c")
        .replace("&", "\\u0026")
    )

    # No user-controlled value is interpolated as markup, a URL, CSS, or executable JS.
    def csp_hash(text):
        return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"

    policy = (
        "default-src 'none'; base-uri 'none'; form-action 'none'; "
        f"script-src {csp_hash(script)}; style-src {csp_hash(style)}; "
        "connect-src 'none'; img-src 'none'; object-src 'none'"
    )
    template = assets.joinpath("offline.html").read_text(encoding="utf-8")
    # One substitution pass prevents template-like names from becoming instructions.
    import re

    replacements = {"POLICY": policy, "STYLE": style, "DATA": data, "SCRIPT": script}
    return re.sub(r"@@(POLICY|STYLE|DATA|SCRIPT)@@", lambda m: replacements[m[1]], template)


def write_report(report: SuiteReport, output: Path, environment: Environment | None = None):
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(render_report(report, environment))
