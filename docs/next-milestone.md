# Next milestone: review workflows and retained identity files

Status: planned handoff, 2026-11-07. TC023, SW030 and EF-008 complete the saved
[previous handoff](governance/handoff-2026-11-05.md). This is one shared five-task
backlog across all three repositories; entries are not implementation approval.

1. **ToolCapsule TC024: standalone difference review.** Render validated retained differences as escaped, script-free HTML with explicit before/after validity, deny-all and budget changes. Preserve evidence limits, bound output and create files exclusively; verify hostile text and narrow-screen layout.
2. **ToolCapsule TC024: source-checked review gate.** Accept an optional explicit pair of before/after summaries before rendering. Reject partial pairs, reversed or replaced evidence before output; preserve read-only inputs and fixed diagnostics.
3. **SimWeave SW031: retained bundle identity contract.** Define a closed schema and bounded duplicate-safe reader for the existing identity summary. Require strict profile/version/digest/byte count and test schema drift, malformed input and SDK mutation.
4. **SimWeave SW031: identity-file review gate.** Verify both canonical byte count and digest from an independent identity file before bundle verification/render/export. Make the file option mutually exclusive with a digest argument; cover equivalent formatting, replacement, bounds and exclusive output in the portable example.
5. **EdgeForge EF-009: source-checked retained review.** Add one bounded CLI workflow that validates a comparison against explicit before/after reports and an optional identity record before HTML export. Compose existing validators, fail before output, and test wrong sources with a matching comparison identity, reversed direction, failed agreement and no inference during review.

Priority: make independently checked evidence usable in review without conflating
internal consistency, source consistency and retained identity. Do not add signing,
execution, service integrations or timing gates. Inspect actual merged state before
branching; EdgeForge's foundational stack may still be open. Keep separate commits
and draft PRs. Merge, deployment and release require separate authorization.
