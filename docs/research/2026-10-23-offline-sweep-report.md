# DirectionBriefV1: Offline HTML sweep reports

- schema_version: 1
- baseline_commit: 573e73acda66573c6f6cb67c4caabbfa32c38456
- scanned_at: 2026-10-23
- coverage: merged milestone, roadmap, architecture, existing contracts and tests,
  open draft status, and primary guidance for this bounded extension.

Finding: The merged sweep-review contract supplies validated parameter-linked summaries, but users must inspect JSON. A static report makes incomplete points and metric comparisons visible without inventing new statistical claims. OWASP guidance supports context-specific HTML encoding; CSP provides an additional defense. Source: [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html).

source_event_date: undated; accessed 2026-10-23; confidence: high;
relevance: offline html sweep reports; direction_alignment: portable verifiable evidence;
opportunity_or_risk: easier evidence review with explicit trust boundaries;
engineering_cost: low; disposition: adopt; roadmap_delta: SW020;
verification_needed: Escaped hostile titles produce no executable tags or event attributes; CSP matches fixed CSS; metric values and evidence hashes match validated summaries; incomplete points withhold metrics; CLI validates before writing and refuses overwrite.

Recommendation: implement this bounded follow-on to the merged milestone.
Broader ABI/broker changes for ToolCapsule and recovery or approval automation for
SimWeave remain separate candidate scopes; they require wider authority or state
transitions than this evidence extension. Evidence gaps: This is a derived descriptive report, not statistical inference, automatic optimization, baseline approval, signature authentication, raw telemetry validation or cross-engine accuracy proof. CSP is defense in depth; escaping is the primary HTML boundary. No browser or UI dependency enters simulation math. Very large accepted reports can be long; tables scroll horizontally on narrow screens.

