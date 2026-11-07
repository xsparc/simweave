# DirectionBriefV1: Bundle identities

- schema_version: 1
- baseline_commit: 316b31bdd56954c57e99553a3cf98e350163fa4d
- scanned_at: 2026-11-07
- coverage: saved milestone, live merged PR/base state, architecture, roadmap, relevant accepted decisions, executable readers/exporters, tests and focused primary serialization documentation.

## Findings

1. Strict structure and semantic consistency are separate checks. Serde supports
   rejecting unknown fields through container attributes; Pydantic strict mode
   prevents ordinary coercion but literal version validation still needs explicit
   type tests. Sources: [Serde attributes](https://serde.rs/container-attrs.html)
   and [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/).
   source_event_date: undated living documentation, accessed 2026-11-07;
   confidence: high; relevance: retained-record intake; direction_alignment:
   reject ambiguous evidence; opportunity_or_risk: coercion and duplicated fields;
   engineering_cost: low; disposition: adopt; roadmap_delta: SW030;
   verification_needed: boolean/float versions, duplicate/missing/unknown fields,
   nested mutations and recomputed semantics.
2. JSON byte identity requires explicit encoder rules and bounded parsing.
   [Python JSON documentation](https://docs.python.org/3/library/json.html)
   describes ordering, separators and parsing hooks. source_event_date: undated
   living documentation, accessed 2026-11-07; confidence: high; relevance:
   normalized identities; direction_alignment: preserve existing byte profiles;
   opportunity_or_risk: confusing normalized, source and original-file digests;
   engineering_cost: low; disposition: adopt; roadmap_delta: SW030;
   verification_needed: equivalent formatting, replacement, explicit byte count,
   bounds and failure-before-output acceptance.

## Overall recommendation and evidence gaps

Implement the saved tasks using existing contracts; preserve separate internal,
source and identity checks. Research informs this explicitly authorized delivery,
not additional scope. No new signing, physical-device validation or security audit
is claimed. Future review-workflow tasks remain planned, not implemented.
