# Next iteration: independently retained review evidence

Status: planned handoff, 2026-11-05. TC022 and SW029 complete the
[previous five tasks](governance/handoff-2026-11-04.md).

1. **ToolCapsule TC023: retained-difference reader.** Add bounded strict intake for the versioned difference envelope, reject duplicates/unknown fields, and recompute changed fields and direction from embedded summaries.
2. **ToolCapsule TC023: explicit-summary verification.** Verify a retained difference against independently provided before/after summaries with CLI acceptance for whole-envelope replacement, reverse direction and no evidence writes. Preserve the distinction from original configuration sources.
3. **SimWeave SW030: bundle canonical identity.** Expose a versioned digest of normalized bundle bytes with explicit newline/number rules and distinction from source-plan digests.
4. **SimWeave SW030: expected bundle identity gate.** Require an optional independently retained digest before bundle review/export; enforce strict digest syntax and fail before output creation.
5. **SimWeave SW030: portable retention acceptance.** Extend the example through digest retention and verification, equivalent formatting and internally consistent replacement; test SDK mutation and byte limits without simulator execution.

Check merged state before branching; keep repository-specific draft PRs and commits.
Planned only; merging, deployment and release require separate authority.
