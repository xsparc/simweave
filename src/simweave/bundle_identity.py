"""Versioned identities for validated, normalized plan-review bundle bytes."""

import hashlib
import hmac
import re

from simweave.plan_bundle import PlanBundle, encode_bundle

ENCODING = "simweave-plan-bundle-json-v1"


def bundle_identity(bundle: PlanBundle) -> dict:
    raw = encode_bundle(bundle)
    return {
        "schema_version": 1,
        "canonicalization": ENCODING,
        "bundle_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "interpretation": "retained_identity_not_attestation",
    }


def verify_bundle_identity(bundle: PlanBundle, expected: str) -> None:
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError("invalid expected bundle digest")
    if not hmac.compare_digest(bundle_identity(bundle)["bundle_sha256"], expected):
        raise ValueError("bundle identity differs")
