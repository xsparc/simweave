# DirectionBriefV1: Verification scope

schema_version: 1
baseline_commit: `b668a45455ec9deb4263f903815e8d470fb59098`
scanned_at: 2026-11-18
coverage: architecture, roadmap, prior ADRs, code/tests and focused primary specifications.

## Findings

- finding: Repeatable hashes require a stable representation; project encodings are not automatically JCS. [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785). source_event_date: 2020-06; accessed 2026-11-18. confidence: high (primary source). relevance: portable evidence. direction_alignment: explicit bounded contracts. opportunity_or_risk: avoid ambiguous interpretation. engineering_cost: bounded reader/CLI tests. disposition: adopt. roadmap_delta: SW038. verification_needed: positive/negative fixtures and preservation checks.
- finding: Wire-format compatibility and interpreted semantics are distinct concerns; explicit local verification scope should not imply provenance. [OTLP compatibility boundary](https://opentelemetry.io/docs/specs/otlp/). source_event_date: living specification, publication date unspecified; accessed 2026-11-18. confidence: high (primary source). relevance: portable evidence. direction_alignment: explicit bounded contracts. opportunity_or_risk: avoid ambiguous interpretation. engineering_cost: bounded reader/CLI tests. disposition: adopt. roadmap_delta: SW038. verification_needed: positive/negative fixtures and preservation checks.

overall_recommendation: implement the approved bounded milestone and queue the shared five-item handoff.
evidence_gaps: synthetic local tests do not prove vendor interoperability, authorship, physical-device performance or hosted service behavior. Broader ecosystem work is outside this focused request.

Integration note: PR #43 merged during delivery. Rebased onto main commit `40567fae8554b0eb8b05c581c2bf9dba0725475b`; the implementation tree was unchanged before this documentation correction.
