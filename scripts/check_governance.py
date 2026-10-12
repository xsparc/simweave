"""Check SimWeave evidence without a dependency on an installed private plugin."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from datetime import date
from pathlib import Path


def check(root: Path, as_of: date | None = None) -> dict:
    errors, warnings = [], []
    try:
        data = tomllib.loads((root / "docs/governance/project-evidence.toml").read_text())
        if data["schema_version"] != 1 or data["project"] != "simweave":
            errors.append("invalid registry identity/version")
        if data["authority"]["dhf_is_authoritative"] is not False:
            errors.append("evidence must remain non-authoritative")
        due = date.fromisoformat(data["review"]["review_due"])
        reviewed = date.fromisoformat(data["review"]["last_reviewed"])
        if reviewed > due:
            errors.append("review dates are reversed")
        if as_of and as_of > due:
            warnings.append("evidence review overdue")
        objectives = {r["id"] for r in data["objectives"]}
        requirements = {r["id"] for r in data["requirements"]}
        seen, designs = set(), set()
        for group in ("objectives", "requirements", "work_items", "research_decisions"):
            for record in data[group]:
                identifier = record["id"]
                if identifier in seen or not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", identifier):
                    errors.append("invalid or duplicate record id")
                seen.add(identifier)
                for field, values in record.items():
                    if field.endswith("_refs"):
                        for reference in values:
                            path = (root / reference).resolve()
                            if not path.is_relative_to(root.resolve()) or not path.is_file():
                                errors.append(f"missing or unsafe reference: {identifier}/{field}")
                    if field == "design_refs":
                        designs.update(values)
                if group == "requirements":
                    if not set(record["objective_ids"]) <= objectives:
                        errors.append("unknown objective")
                    if record["status"] == "implemented":
                        for field in (
                            "roadmap_refs",
                            "design_refs",
                            "implementation_refs",
                            "verification_refs",
                            "validation_refs",
                            "risk_refs",
                        ):
                            if not record.get(field):
                                errors.append(f"incomplete traceability: {identifier}/{field}")
                if group == "work_items":
                    if not set(record["requirement_ids"]) <= requirements:
                        errors.append("unknown requirement")
                    if record["status"] in {"in-progress", "verified", "closed", "approved"}:
                        if not re.fullmatch(
                            r"conversation:\d{4}-\d{2}-\d{2}-[a-z0-9-]+",
                            record.get("approval_ref", ""),
                        ):
                            errors.append("missing bounded approval")
                    if record["status"] in {"verified", "closed"} and not record.get(
                        "evidence_refs"
                    ):
                        errors.append("closed work lacks evidence")
        for adr in (root / "docs/architecture/decisions").rglob("*.md"):
            if (
                "Status: accepted" in adr.read_text()
                and adr.relative_to(root).as_posix() not in designs
            ):
                errors.append("accepted ADR is unindexed")
    except (OSError, ValueError, KeyError, TypeError):
        errors.append("registry unreadable or malformed")
    return {
        "status": "fail" if errors else "warn" if warnings else "pass",
        "errors": errors,
        "warnings": warnings,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = check(Path(__file__).resolve().parents[1], args.as_of)
    print(json.dumps(report, indent=2))
    raise SystemExit(2 if report["errors"] or (args.strict and report["warnings"]) else 0)
