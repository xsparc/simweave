# DirectionBrief: Identity file export

scanned_at: 2026-11-15
Baseline: `8b8fcf8fa4e1b5019a727e3bbb5084f2014a2e3b`. Coverage: current architecture, roadmap, accepted prior decision,
implementation and tests for the saved five-item handoff; focused standards review.

## Findings

- Source: [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785), published 2020-06,
  accessed 2026-11-15. Confidence: high (primary standard). Stable serialization is
  necessary for repeatable hashes. Relevance/alignment: portable retained evidence.
  Opportunity: version existing project encodings and pin vectors; risk: confusing
  normalized identity with original bytes or signatures. Cost: bounded tests/docs.
  Disposition: adopt explicit encoding descriptions, not a claim of JCS compliance.
- Source: [JSON Schema object reference](https://json-schema.org/understanding-json-schema/reference/object),
  living documentation (publication date unspecified), accessed 2026-11-15.
  Confidence: high (official documentation). Required properties and rejection of
  additional properties are separate constraints. Opportunity: keep closed records
  aligned with strict readers. Risk: schema structure alone cannot enforce derived
  evidence consistency. Cost: reuse readers and negative tests. Disposition: adopted.

## Direction and verification

Implement SW036 as defined in the saved handoff; no dependency or runtime-policy
change. Roadmap delta: complete this slice and queue the five tasks in
`docs/next-milestone.md`. Verify bounded reads, exclusive output where applicable,
independent target checks and unchanged inputs. Evidence gaps: local synthetic
acceptance cannot establish provenance, production performance or cross-platform
runtime support. No new market or competitor claim is made.
