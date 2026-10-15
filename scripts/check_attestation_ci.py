"""Verify a real signed catalog and four provenance policy negative controls."""

import argparse
import json
from pathlib import Path

from simweave.attestation import AttestationPolicy, verify_catalog
from simweave.catalog_archive import export_catalog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    policy = AttestationPolicy(
        repository=args.repository,
        workflow=".github/workflows/trusted-evidence.yml",
        source_ref=args.ref,
        source_digest=args.commit,
    )
    (args.output / "policy.json").write_text(policy.model_dump_json(indent=2), encoding="utf-8")
    receipt = verify_catalog(
        args.archive, args.bundle, policy, destination=args.output / "restored.db"
    )
    export_catalog(args.output / "restored.db", args.output / "reexport.ndjson")
    assert args.archive.read_bytes() == (args.output / "reexport.ndjson").read_bytes()
    failures = []
    for name, change in (
        ("repository", {"repository": "untrusted-owner/untrusted-repository"}),
        ("workflow", {"workflow": ".github/workflows/untrusted.yml"}),
        ("ref", {"source_ref": "refs/heads/untrusted"}),
        ("commit", {"source_digest": "0" * 40}),
    ):
        try:
            verify_catalog(
                args.archive,
                args.bundle,
                AttestationPolicy.model_validate({**policy.model_dump(), **change}),
            )
        except ValueError:
            failures.append(name)
        else:
            raise AssertionError("untrusted provenance accepted")
    tampered = args.output / "tampered.ndjson"
    tampered.write_bytes(args.archive.read_bytes() + b"\n")
    try:
        verify_catalog(tampered, args.bundle, policy, destination=args.output / "never.db")
    except ValueError:
        failures.append("artifact bytes")
    else:
        raise AssertionError("tampered archive accepted")
    assert not (args.output / "never.db").exists()
    result = {"receipt": receipt, "rejected": failures}
    (args.output / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
