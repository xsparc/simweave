# Adapter deltas and source-bound plan review

Status: accepted, 2026-10-29. Scope: three SW026 tasks from the saved handoff.

Keep PlanDifference v1, default JSON, its schema and HTML output compatible.
Opt-in version 2 adds adapter_deltas in before order followed by previously
unseen after adapters. Each row has before/after runs and steps and signed
changes. Missing adapters have zero counts. Validate row arithmetic, presence,
union order and both global sums; delta sums follow from those constraints.

Expose version 2 through `--schema-version 2` on sweep-diff and sweep-diff-schema.
CSV always uses the v2 data: one global row and one row per union adapter with
explicit after_minus_before direction, source/Suite identities and counts.
Prefix free-text labels with text:, quote every cell and preserve UTF-8/CRLF.
Keep 64 KiB input/output limits and exclusive output creation. Global and adapter
rows are different scopes; do not add a global row to adapter totals.

The read-only sweep-diff-verify command parses a v1 or v2 report, independently
admits both sources, recomputes the expected report and compares all fields.
It rejects changed counts, identities, names, direction and adapter details.
Verification checks local source consistency, not a signature, independent
execution evidence, numerical equivalence, reservations or adapter availability.
HTML remains v1; requesting v2 HTML fails explicitly until its own follow-up.

Acceptance includes legacy behavior, union ordering, zero counts, sum invariants,
version rejection, numeric CSV round trips, hostile labels, exact bytes,
exclusive creation, file bounds and unchanged verification inputs.
