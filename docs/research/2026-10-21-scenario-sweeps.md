# DirectionBriefV1: bounded experiment authoring

- schema_version: 1
- baseline_commit: 4e5e50152d8fae7f37fd50a73dfa0696915ffda3
- scanned_at: 2026-10-21
- coverage: merged SW017, Suite/Scenario contracts, execution and calibration
  boundaries, primary Python Cartesian-product semantics and simulator interfaces.

Finding: suites already validate a bounded scenario/adapter/seed/controller
matrix, but parameter variants require repeated handwritten scenarios. Python's
[itertools.product](https://docs.python.org/3/library/itertools.html#itertools.product)
defines deterministic Cartesian expansion in input order. A closed parameter
planner can reuse existing Suite validation and evidence without a new executor.
source_event_date: undated living documentation, accessed 2026-10-21;
confidence: high; relevance: repeatable experiment authoring;
direction_alignment: portable bounded experiments; opportunity_or_risk: fewer
manual variant errors versus combinatorial growth and selection bias;
engineering_cost: medium; disposition: adopt; roadmap_delta: SW018 plan-only
scenario sweeps; verification_needed: strict axes, full preflight bounds, stable
ordering/digests, exclusive output and execution through existing adapters.

Overall recommendation: add explicit bounded grids before adaptive tuning or new
simulator integrations. Existing calibration limits still apply to repeated
comparisons. Evidence gaps: no claim of physical coverage, new robot support,
cross-engine equality or corrected family-wise inference; real ROS is unchanged.
