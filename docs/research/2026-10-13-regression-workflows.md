# Accepted direction: regression workflows

DirectionBriefV1; schema_version: 1. Baseline:
`0bdedee51f9c373f6e1cabf90402b5f81693cf02`. Scanned: 2026-10-13.
Coverage: approved user workflow, current implementation and tests, CI artifact
interoperability, simulator repeatability, and bounded-input security.

1. GitHub supports matrix jobs and retained test artifacts. Adopt versioned suite
   matrices and JSON/JUnit with portable recordings. High confidence/relevance;
   aligns with CI interoperability. Opportunity: make bad controller tuning a
   visible build failure. Medium engineering cost. Roadmap delta: SW005 suite
   runner. Verification: two controllers, ten seeds, two real engines, positive
   and negative exit-code checks. Source event date: undated current docs,
   accessed 2026-10-13. [Matrices](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations),
   [artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts).
2. MuJoCo scopes exact repeatability to runtime/version conditions. Adopt
   same-input comparisons with explicit metric deltas and environment warnings.
   High technical confidence/relevance; medium product-priority confidence.
   Aligns with auditable experiment review. Risk: treating incomparable runs or
   downsampled charts as proof. Medium engineering cost. Roadmap delta: SW005
   comparison view. Verification: reject confounded pairs, compare real runs,
   browser failure inspection/export. Source event date: undated current docs,
   accessed 2026-10-13. [MuJoCo computation](https://mujoco.readthedocs.io/en/stable/computation/index.html).

Overall recommendation: deliver the two explicitly accepted directions as ADR
0003. Evidence gaps: broader user research, representative fleet workloads,
multi-host execution, and cross-environment reproducibility. New milestone
proposals remain advisory and do not expand this implementation.
