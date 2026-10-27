# DirectionBriefV1: Sweep capacity report

- schema_version: 1
- baseline_commit: 98c1e8cde3220e73abaa552af4988433fd87ee27
- scanned_at: 2026-10-27
- coverage: repository roadmap, architecture, merged and open PRs, current contracts and tests, primary security guidance.

Finding: The merged preview already gives trusted planned counts; operators must manually subtract limits and sum adapter rows. A derived report removes that arithmetic without adding a scheduler. OWASP contextual output encoding supports safely rendering user-provided names; CSP is additional protection.

Source: [OWASP guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html).
source_event_date: undated living documentation, accessed 2026-10-27;
confidence: high; relevance: sweep capacity report; direction_alignment: explicit bounded workflows;
opportunity_or_risk: expose remaining admission headroom without implying resource reservations or successful execution;
engineering_cost: low; disposition: adopt; roadmap_delta: SW023;
verification_needed: Remaining capacity reaches zero at each admission boundary; adapter totals equal workload totals in declared order. Default JSON is unchanged. Invalid/over-budget input produces no report, output never overwrites, hostile text is escaped, and contract constants reject non-integer values.

Overall recommendation: complete the merged workload-preview workflow with
capacity arithmetic and offline review. Recovery and scheduling changes are
larger independent scopes with operational dependencies; neither is required
to derive these counts from an already admitted plan.

Evidence gaps: Capacity is planned admission headroom, not reserved resources, adapter availability or a time/memory/storage/cost estimate. No simulation, queue scheduling or baseline decision occurs. Reports are unsigned derived evidence; execution independently validates its input.
