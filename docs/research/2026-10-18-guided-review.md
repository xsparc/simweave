# DirectionBriefV1: complete baseline review

- schema_version: 1
- baseline_commit: 622c2c1
- scanned_at: 2026-10-18
- coverage: focused workspace gaps, existing role/generation contracts and accessible confirmation.

1. finding: modal dialogs keep interaction within the dialog and support Escape,
   deliberate initial focus and return focus.
   [W3C dialog guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
   source_event_date: undated, accessed 2026-10-18; confidence: high;
   relevance: explicit baseline approvals; direction_alignment: usable review;
   opportunity_or_risk: accidental or stale approval; engineering_cost: medium;
   disposition: adopt; roadmap_delta: SW014; verification_needed: keyboard
   cancellation/confirmation, concurrent generation rejection and two-tenant tests.
2. finding: the existing workspace creates comparisons but directs approvals to
   the API; ADRs 0005/0006 already define immutable generation-checked decisions.
   source_event_date: repository baseline above; confidence: high;
   relevance: incomplete reviewer workflow; direction_alignment: bounded reuse;
   opportunity_or_risk: complete review without broadening roles;
   engineering_cost: medium; disposition: adopt; roadmap_delta: SW014;
   verification_needed: approver-only writes, readable 30-pair comparisons and history.

Overall recommendation: select guided review ahead of incremental recovery, which
needs a separate copy/resume protocol, and ABI/provider expansion unrelated to this
workflow. Selection is authorized by the 2026-10-18 delegated research/delivery
request. Evidence gaps: screen-reader certification, physical multi-host validation
and statistical calibration; none is claimed by the browser checks.
