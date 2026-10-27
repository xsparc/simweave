# DirectionBriefV1: Capacity export contracts

- schema_version: 1
- baseline_commit: 4ee47e98bc849b732cba91a4cf27f0e3acf1536b
- scanned_at: 2026-10-27
- coverage: repository roadmap, architecture, merged and open PRs, current contracts and tests, primary security guidance.

Finding: The merged capacity format lacks its own CLI schema and tabular export, and duplicates suite limits in report arithmetic. Pydantic provides schema generation from models; using that existing mechanism avoids a handwritten schema. Shared limits prevent reporting and admission from diverging.

Source: [OWASP guidance](https://docs.pydantic.dev/latest/concepts/json_schema/).
source_event_date: undated living documentation, accessed 2026-10-27;
confidence: high; relevance: capacity export contracts; direction_alignment: explicit bounded workflows;
opportunity_or_risk: make capacity reports usable by integrations while avoiding admission/report drift;
engineering_cost: low; disposition: adopt; roadmap_delta: SW024;
verification_needed: Generated schema exposes closed nested contracts and shared limits. CSV round-trips hostile labels, sums adapter totals correctly, preserves identities/order and exact CLI bytes, and never overwrites files. Invalid and over-budget plans fail before output. Existing capacity boundary and full suite tests pass.

CSV research: spreadsheet applications may interpret formula-leading cells.
The existing project export convention prefixes free-text labels with text:;
this slice preserves that convention and tests quoting and delimiters.
Source: [OWASP CSV injection](https://community.owasp.org/attacks/CSV_Injection),
undated, accessed 2026-10-27. Confidence: high for the documented risk; no claim
of validation across spreadsheet applications. Disposition: adopt.

Overall recommendation: complete the existing capacity integration contract
before adding a scheduler. The previous five-item iteration is complete in
PRs #28 and xsparc/toolcapsule#20, with no pending handoff; these items initialize
the next bounded iteration.

Evidence gaps: CSV headroom is for the entire plan and is repeated on each adapter row; it is not per-adapter quota and must not be summed. Labels are deliberately prefixed; stripping the prefix can reintroduce spreadsheet formula risks. JSON Schema describes structure, not proof that a report derives from a valid plan. Reports remain unsigned planned counts, without execution, availability checks or resource estimates.
