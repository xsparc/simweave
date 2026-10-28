# Next iteration: configuration trust and plan comparison

Status: planned handoff, 2026-10-27. These five tasks are not implemented in
TC017/SW024. The next run should recheck merged PRs and branch dependencies
before starting; preserve existing work and avoid duplicate implementation.

1. **ToolCapsule: offline trust-store validation.** Add a bounded, read-only
   `trust-check` command for key IDs and Ed25519 public-key encoding. Report counts
   without echoing keys. Accept empty stores as deny-all. Reject malformed keys,
   duplicate JSON key IDs and oversized files; do not load signing seeds or
   claim that a syntactically valid key is trusted by anyone else.
2. **ToolCapsule: budget-fit report.** Compare an explicit Limits file against an
   explicit host Policy and report which requested budgets exceed maxima. Reuse
   admission comparisons to avoid drift. No policy rewriting, package signing,
   execution or authority grant. Test equality, each exceeded field and invalid
   input; make clear that fitting budgets alone does not admit a package.
3. **SimWeave: plan-difference contract.** Compare two admitted Sweep inputs in a
   pure versioned model, with source identities and signed run/step/headroom
   changes, plus adapter additions/removals. Validate both plans before output;
   do not simulate or infer numerical result equivalence.
4. **SimWeave: plan-difference CLI.** Expose bounded JSON comparison with exclusive
   output creation. Preserve direction (before versus after), deterministic
   ordering and exit behavior. Test invalid/oversized input and unchanged plans.
5. **SimWeave: offline plan-difference HTML.** Render the same validated comparison
   with escaped text, script-free CSP and clear before/after counts. Verify
   identity parity with JSON, hostile labels and desktop/mobile overflow.

Priority rationale: configuration checks naturally extend to the remaining
operator-supplied trust file and budget compatibility; capacity reports now
provide the inputs for reviewing plan changes before execution. These scopes
reuse current contracts and avoid new runtime, broker or scheduler boundaries.

Expected milestones: TC018 (items 1–2), SW025 (items 3–5). Each repository needs
its own implementation, tests, ADR/evidence update and draft PR. Reuse the patched
ToolCapsule branch while security PR #18 remains open; if it has merged, use main.
Merging, release, deployment and automatic baseline approval remain out of scope.
