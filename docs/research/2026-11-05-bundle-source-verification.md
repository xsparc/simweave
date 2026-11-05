# DirectionBriefV1: Bundle source verification

- schema_version: 1
- baseline_commit: 8866d788c4045a9cf4970cc1e92f1ad17918fbcb
- scanned_at: 2026-11-05
- coverage: saved handoff, merged PR state, architecture, roadmap, accepted decisions, readers, exporters and tests.

Finding: deterministic hashing requires an explicit invariant serialization profile.
[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785), published June 2020,
provides JCS; this delivery does not claim JCS implementation.
[Python JSON documentation](https://docs.python.org/3/library/json.html)
defines sorting, compact separators and nonfinite-number handling.
[Python CSV documentation](https://docs.python.org/3/library/csv.html)
defines dialect/newline behavior, supporting exact exporter-byte verification.
The Python pages are undated living documentation; accessed 2026-11-05.

confidence: high; relevance: bounded retained evidence;
direction_alignment: independent source/identity checks;
opportunity_or_risk: internal consistency can be mistaken for independent provenance;
engineering_cost: medium; disposition: adopt; roadmap_delta: SW029;
verification_needed: mutation, reverse direction, replacement, exact bytes and no writes on invalid input.

Recommendation: complete the saved scope using existing normalized models and
explicit evidence boundaries. For EdgeForge, version the Python encoding rather
than asserting RFC 8785 compatibility. Research informs design, not authority.
Evidence gaps: no independent security audit, signature or physical-device validation.
