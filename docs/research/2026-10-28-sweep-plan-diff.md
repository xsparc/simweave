# DirectionBriefV1: Directional sweep plan comparison

- schema_version: 1
- baseline_commit: 0367816335f5a5f5adbcc2799789fcaf2801a79d
- scanned_at: 2026-10-28
- coverage: repository roadmap, architecture, merged and open PRs, current contracts and tests, primary security guidance.

Finding: The recorded handoff builds on capacity reports to compare changes before execution. Equal workload counts can hide different seeds or scenarios, so source identities must remain visible. OWASP contextual encoding guidance supports escaped names in HTML, with CSP as additional protection.

Source: [OWASP guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html).
source_event_date: undated living documentation, accessed 2026-10-28;
confidence: high; relevance: directional sweep plan comparison; direction_alignment: explicit bounded workflows;
opportunity_or_risk: show workload changes without implying that equal counts mean equivalent experiments;
engineering_cost: low; disposition: adopt; roadmap_delta: SW025;
verification_needed: Direction reversal negates deltas; adapter additions/removals preserve declared order; identical inputs are explicit and changed experiments with equal counts are not called identical. Both mutated/over-budget sources fail before rendering. Contracts reject inconsistent summaries and noninteger schema versions. CLI rejects oversized inputs without output and never overwrites. HTML preserves JSON identities/counts, escapes hostile names and passes desktop/mobile checks.

Overall recommendation: implement the recorded SW025 handoff with explicit
direction, normalized source identities and independent admission of each plan.
Scheduling and automatic tuning remain separate scopes requiring operational
or statistical acceptance evidence.

Evidence gaps: Reports compare planned counts, not execution results, physics equivalence, availability, reservations or runtime estimates. Identical inputs means equal normalized Sweep digests. Internal report consistency is not proof of source provenance; comparisons must be generated from independently admitted inputs. No simulation, scheduling, optimization or baseline approval occurs.
