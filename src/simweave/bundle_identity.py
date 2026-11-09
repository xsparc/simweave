"""Versioned identities for validated, normalized plan-review bundle bytes."""

import hashlib
import hmac
import re
from typing import Literal

from pydantic import Field, field_validator

from simweave.contracts import Contract
from simweave.plan_bundle import MAX_BUNDLE, PlanBundle, decode_json, encode_bundle

ENCODING = "simweave-plan-bundle-json-v1"
MAX_IDENTITY_BYTES = 4096


class BundleIdentity(Contract):
    schema_version: Literal[1]
    canonicalization: Literal["simweave-plan-bundle-json-v1"]
    bundle_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=1, le=MAX_BUNDLE)
    interpretation: Literal["retained_identity_not_attestation"]

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("identity version must be an integer")
        return value


def read_bundle_identity(raw: bytes) -> BundleIdentity:
    if len(raw) > MAX_IDENTITY_BYTES:
        raise ValueError("identity exceeds byte limit")
    return BundleIdentity.model_validate(decode_json(raw))


def verify_bundle_identity_record(bundle: PlanBundle, identity: BundleIdentity) -> None:
    retained = BundleIdentity.model_validate(identity.model_dump())
    actual = bundle_identity(bundle)
    if retained.bytes != actual["bytes"] or not hmac.compare_digest(
        retained.bundle_sha256, actual["bundle_sha256"]
    ):
        raise ValueError("bundle identity record differs")


def bundle_identity(bundle: PlanBundle) -> dict:
    raw = encode_bundle(bundle)
    return BundleIdentity.model_validate(
        {
            "schema_version": 1,
            "canonicalization": ENCODING,
            "bundle_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "interpretation": "retained_identity_not_attestation",
        }
    ).model_dump()


def verify_bundle_identity(bundle: PlanBundle, expected: str) -> None:
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError("invalid expected bundle digest")
    if not hmac.compare_digest(bundle_identity(bundle)["bundle_sha256"], expected):
        raise ValueError("bundle identity differs")
