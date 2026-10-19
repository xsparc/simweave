# DirectionBriefV1: calibrate decision interpretation

- schema_version: 1
- baseline_commit: e360dfb
- scanned_at: 2026-10-19
- coverage: focused bootstrap interpretation, existing decision policy and next-step evidence gaps.

1. finding: SciPy distinguishes percentile, basic and BCa bootstrap intervals,
   supports paired resampling, and documents degenerate-distribution limitations.
   [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).
   source_event_date: living documentation, accessed 2026-10-19; confidence: high;
   relevance: SimWeave uses a paired percentile mean interval, not SciPy's default
   BCa method; direction_alignment: reliable decisions; opportunity_or_risk:
   avoid conflating nominal coverage with measured coverage; engineering_cost:
   medium; disposition: adopt; roadmap_delta: SW015 synthetic calibration;
   verification_needed: seeded null/shifted/skewed trials and independent checks.
2. finding: the 2026-10-16 direction brief proposed 1,000 null/shifted trials;
   guided review now exposes those decisions to approvers.
   source_event_date: repository briefs and e360dfb baseline; confidence: high;
   relevance: interpretation gap; direction_alignment: review usability;
   opportunity_or_risk: visible numbers may imply unsupported certainty;
   engineering_cost: medium; disposition: adopt; roadmap_delta: SW015;
   verification_needed: report rates, denominators, uncertainty and non-scope.

Overall recommendation: implement synthetic calibration and an interpretation guide
before altering the statistical policy or expanding recovery. Scope selection and
draft delivery follow the continuing delegated next-milestone request.
Evidence gaps: dependent real simulator seeds, repeated-build/multiple-metric error
control and external statistical review. Synthetic results cannot fill those gaps.
