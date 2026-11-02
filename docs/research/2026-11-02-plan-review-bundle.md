# DirectionBriefV1: retained plan-review evidence

- schema_version: 1
- baseline_commit: 1a23e05d2505dd467212b56aa0417aa9069d2d55
- scanned_at: 2026-11-02
- coverage: focused JSON intake and Pydantic contract validation for SW028;
  no simulator or hosted-service change.

1. finding: JSON intake should bound input before decoding; repeated keys need an
   explicit policy. [Python JSON](https://docs.python.org/3/library/json.html).
   source_event_date: living documentation, accessed 2026-11-02;
   confidence: high; relevance: retained untrusted plans; direction_alignment: portability;
   opportunity_or_risk: ambiguous keys and resource exhaustion;
   engineering_cost: low; disposition: adopt; roadmap_delta: delegated SW028;
   verification_needed: bounded reads, duplicate keys, nesting and malformed UTF-8.
2. finding: model validation and model copying have different guarantees; retained
   evidence must be recomputed from validated data.
   [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/).
   source_event_date: living documentation, accessed 2026-11-02;
   confidence: high; relevance: mutated nested models; direction_alignment: evidence integrity;
   opportunity_or_risk: internally plausible reports may refer to different plans;
   engineering_cost: medium; disposition: adopt; roadmap_delta: delegated SW028;
   verification_needed: nested mutation, changed identity, reversed sources and export round trips.

Overall recommendation: deliver a closed portable envelope using the existing
comparison and rendering contracts. Evidence gaps: consistent retained data is
not signed provenance, simulator execution, runtime capacity or physical equivalence.
