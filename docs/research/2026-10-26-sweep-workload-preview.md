# DirectionBriefV1: Sweep workload preview

- schema_version: 1
- baseline_commit: f9dd7490d2636d019637193c73170eb17c8f8cc2
- scanned_at: 2026-10-26
- coverage: roadmap, architecture, current CLI and runtime/planner contracts,
  recent merges, open draft status, existing tests and primary platform guidance.

Finding: Sweep planning already enumerates an ordered Cartesian grid, but users must manually account for adapters, seeds and the two controller roles to understand total work. Deriving counts from the admitted Suite expansion exposes that multiplication without duplicating admission rules. Python documents deterministic product order, matching the existing planner's construction.

Source: [Python itertools.product documentation](https://docs.python.org/3/library/itertools.html#itertools.product).
source_event_date: undated living documentation, accessed 2026-10-26;
confidence: high, checked against local pinned-runtime regressions;
relevance: sweep workload preview; direction_alignment: explicit bounded work;
opportunity_or_risk: clearer workload control without implicit authority;
engineering_cost: low; disposition: adopt; roadmap_delta: SW022;
verification_needed: Counts independently equal expanded runs/steps for multiple axes/adapters/seeds; ordering and suite identity match the planner; no simulation is invoked; over-budget, invalid and mutated inputs fail; schema version is strict; CLI byte bounds and exclusive output hold.

Overall recommendation: implement the bounded existing-contract extension.
Distributed recovery requires a larger state migration design. Statistical optimization needs explicit selection and multiple-comparison policy. This preview instead closes an authoring gap using the existing admitted expansion.

Evidence gaps: Counts are planned work, not wall-clock, memory, storage or monetary estimates. A valid plan does not establish installed adapter availability or successful execution. Rejected over-budget plans produce no partial report. Reports are unsigned derived evidence; execution must independently validate the Suite. No queue scheduling, simulation, automatic optimization or baseline decision occurs.

