# DirectionBriefV1: parameter-linked result review

- schema_version: 1
- baseline_commit: 3c13c265d0dbcdd4d1b6c1aebcd81c609bffcbd7
- scanned_at: 2026-10-22
- coverage: merged SW018, SuiteReport validation and comparison warnings, calibration
  limits and primary experimental-design guidance. Focused on sweep interpretation.

Finding: sweep planning creates explicit combinations, but reviewing their results
requires mapping individual cases back to parameter points. [NIST's full-factorial
explanation](https://www.itl.nist.gov/div898/handbook/pri/section3/pri333.htm) identifies
combinations of factor settings as the experiment structure. Preserving those
settings in summaries is a useful project-specific extension to the existing plan.
source_event_date: undated handbook, accessed 2026-10-22; confidence: high;
relevance: trace results to explicit inputs; direction_alignment: portable evidence;
opportunity_or_risk: easier review versus hiding failed seeds or overclaiming
inference; engineering_cost: medium; disposition: adopt; roadmap_delta: SW019
parameter-linked descriptive review; verification_needed: exact plan/report match,
no cross-adapter pooling, missing-pair visibility and bounded CLI contracts.

Overall recommendation: summarize completed grid evidence before adaptive search.
The implementation does not perform factorial effect estimation or statistical
inference; the source motivates preserving experimental structure only. Evidence
gaps: summary validation does not verify raw telemetry, provenance or physical
accuracy; existing calibration and multiple-comparison limitations still apply.
