# DirectionBriefV1: Identity record check

schema_version: 1
baseline_commit: `910a9d36f4dbeb640fe8b0f497d178bfe2ef00f2`
scanned_at: 2026-11-15
coverage: saved milestone, architecture/roadmap, prior accepted ADR, affected code,
tests and focused primary specifications for portable evidence.

## Findings

1. finding: required properties and rejection of additional properties are distinct
   constraints. [JSON Schema object reference](https://json-schema.org/understanding-json-schema/reference/object).
   source_event_date: unspecified living documentation; accessed 2026-11-15.
   confidence: high. relevance: closed retained records. direction_alignment:
   explicit contracts. opportunity_or_risk: schema structure does not replace raw
   byte limits, duplicate rejection or semantic checks. engineering_cost: small,
   reuse existing readers. disposition: adopt. roadmap_delta: implement SW037.
   verification_needed: malformed, missing, duplicate and type-confusion cases.
2. finding: repeatable hashing requires a stable representation.
   [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785).
   source_event_date: 2020-06; accessed 2026-11-15. confidence: high (primary RFC).
   relevance: normalized identity and exact exports. direction_alignment: versioned
   evidence. opportunity_or_risk: content consistency can be mistaken for provenance.
   engineering_cost: bounded acceptance tests and explicit interpretation text.
   disposition: adopt. roadmap_delta: retain existing project encodings and document
   verification scope; no JCS claim. verification_needed: byte preservation,
   mismatches and independent source checks.

## Recommendation and gaps

overall_recommendation: deliver the approved saved handoff using existing strict
contracts; queue the next five acceptance-scoped tasks in docs/next-milestone.md.
evidence_gaps: synthetic local evidence does not prove authorship, production
performance or physical-device behavior. This focused request does not require a
broader competitor scan; no dependency or runtime-policy change is proposed.
