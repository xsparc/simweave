"""Closed, bounded portable evidence containing sources and their v2 comparison."""

import json
from typing import Literal

from pydantic import field_validator, model_validator

from simweave.contracts import Contract, canonical
from simweave.sweep_diff import PlanDifferenceV2, compare_plans
from simweave.sweeps import Sweep

MAX_COMPONENT = 65_536
MAX_BUNDLE = 3 * MAX_COMPONENT


class PlanBundle(Contract):
    schema_version: Literal[1]
    before: Sweep
    after: Sweep
    comparison: PlanDifferenceV2
    interpretation: Literal["local_source_consistency_only"] = "local_source_consistency_only"

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("bundle version must be an integer")
        return value

    @model_validator(mode="after")
    def consistent(self):
        for component in (self.before, self.after, self.comparison):
            if len(canonical(component.model_dump()).encode("utf-8")) > MAX_COMPONENT:
                raise ValueError("bundle component exceeds byte limit")
        expected = compare_plans(self.before, self.after, schema_version=2)
        if self.comparison != expected:
            raise ValueError("bundle comparison differs from retained sources")
        return self


def create_bundle(before: Sweep, after: Sweep) -> PlanBundle:
    # Dump/revalidate to reject mutations of frozen models' nested lists/dicts.
    return PlanBundle.model_validate(
        {
            "schema_version": 1,
            "before": before.model_dump(),
            "after": after.model_dump(),
            "comparison": compare_plans(before, after, schema_version=2).model_dump(),
        }
    )


def encode_bundle(bundle: PlanBundle) -> bytes:
    checked = PlanBundle.model_validate(bundle.model_dump())
    raw = (canonical(checked.model_dump()) + "\n").encode("utf-8")
    if len(raw) > MAX_BUNDLE:
        raise ValueError("bundle exceeds byte limit")
    return raw


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate bundle key")
        result[key] = value
    return result


def decode_json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except RecursionError:
        raise ValueError("bundle nesting exceeds limit") from None


def read_bundle(raw: bytes) -> PlanBundle:
    if len(raw) > MAX_BUNDLE:
        raise ValueError("bundle exceeds byte limit")
    return PlanBundle.model_validate(decode_json(raw))
