"""Closed response contract for completed local plan-bundle verification."""

from typing import Literal

from pydantic import field_validator

from simweave.contracts import Contract
from simweave.plan_bundle import decode_json

MAX_VERIFICATION_RESPONSE_BYTES = 4096


class BundleVerificationResponse(Contract):
    schema_version: Literal[1]
    verified: Literal[True]
    source_checked: bool
    identity_checked: bool
    interpretation: Literal["local_source_consistency_only"]

    @field_validator("schema_version", "verified", mode="before")
    @classmethod
    def exact_literal_types(cls, value, info):
        expected = int if info.field_name == "schema_version" else bool
        if type(value) is not expected:
            raise ValueError("incorrect verification response field type")
        return value


def read_bundle_verification_response(raw: bytes) -> BundleVerificationResponse:
    """Validate a response's shape, not whether its stated checks actually ran."""
    if len(raw) > MAX_VERIFICATION_RESPONSE_BYTES:
        raise ValueError("verification response exceeds byte limit")
    try:
        return BundleVerificationResponse.model_validate(decode_json(raw))
    except ValueError:
        # JSON and model errors may include untrusted field names or values.
        raise ValueError("invalid bundle verification response") from None
