# Next iteration: validation diagnostics and plan-review exports

Status: planned handoff, 2026-10-28. These five tasks are not implemented in
TC018/SW025. The [previous handoff](governance/handoff-2026-10-27.md) is completed
by the current trust/budget checks and directional plan-comparison work.

1. **ToolCapsule TC019: structured validation errors.** Add an opt-in JSON error
   mode for configuration/trust/budget checks with stable error codes and no
   input values, key IDs, key material or paths. Preserve default stderr and
   existing 0/1/2 exit meanings. Test malformed input, I/O and non-fitting budgets.
2. **ToolCapsule TC019: configuration workflow acceptance fixture.** Add a bounded
   synthetic workflow that generates templates and a public trust store, checks
   configuration, signs a known fixture, verifies budget fit and package preflight,
   then demonstrates explicit allowlist and budget denial. Exercise it in CI
   without ambient guest permissions or real operator files.
3. **SimWeave SW026: per-adapter plan deltas.** Extend plan comparison with ordered
   before/after run and step totals for every adapter in the union, including
   zero counts for added/removed adapters. Totals must sum to global deltas.
   Define backward-compatible output/version behavior and no equivalence claims.
4. **SimWeave SW026: plan-difference CSV.** Export the validated comparison with
   explicit direction, adapter/global counts and identities. Reuse text-prefixed
   labels, exact UTF-8/CRLF, byte bounds and exclusive output. Test hostile labels,
   numeric round trips and added/removed adapters.
5. **SimWeave SW026: source-bound comparison verification.** Add a read-only
   command that takes both Sweep sources and a JSON comparison, recomputes the
   expected report and rejects altered counts, identities or reversed direction.
   Bound all files and avoid rewriting evidence. Document that this is local
   consistency checking, not a signature or independent execution attestation.

Priority rationale: validation commands need stable automation diagnostics and
an end-to-end authoring check; directional comparisons need adapter-level detail,
portable tabular review and verification against retained source plans.

Each repository needs its own tests, ADR/evidence updates and draft PR. Check
merge state before starting to avoid duplicate implementation. ToolCapsule should
use the patched dependency branch while security PR #18 remains open, otherwise
main. Merge, deployment, release, paid execution and automatic baseline approval
remain outside this handoff.
