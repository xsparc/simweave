# Next iteration: portable configuration and comparison evidence

Status: planned handoff, 2026-10-31. TC020/SW027 completed the archived
[previous five tasks](governance/handoff-2026-10-29.md).

1. **ToolCapsule TC021: strict retained configuration-result reader.** Validate
   the v1 envelope and cross-field relationships; reject contradictory validity,
   budget status and deny-all indicators. Add bounded read-only CLI intake and
   fixtures for every valid and invalid result shape. No package admission.
2. **ToolCapsule TC021: source-bound configuration verification.** Recompute a
   retained result against explicit limits/policy/trust files, reject mismatch,
   and report local consistency only. Preserve fixed diagnostics, no input echo,
   and no writes or execution. Document that identical summaries do not identify
   identical keys or policies and provide no attestation.
3. **SimWeave SW028: canonical plan-review bundle.** Define a bounded closed
   JSON envelope containing both source plans and their v2 comparison, with
   explicit version and identity rules; revalidate all contents without execution.
4. **SimWeave SW028: portable bundle import/export commands.** Create envelopes
   exclusively and verify retained envelopes with fixed diagnostics. Reject
   tampering, excess input and unsupported versions; do not install adapters,
   fetch assets, create jobs or interpret embedded paths.
5. **SimWeave SW028: bundle acceptance and documentation.** Exercise export,
   offline verification and rendering from one retained envelope using the
   synthetic plan-review example, including altered identities, reverse direction
   and desktop/mobile review. Preserve existing two-source CLI behavior.

Priority: configuration and plan-review outputs now have portable contracts;
next make retained evidence safely checkable without broadening execution.
Check merge state first: TC020 targets the security branch while PR #18 remains
open; SW027 targets main. Keep separate repository commits and draft PRs.
These tasks are planned only. Merging, release, deployment, paid services and
baseline approval remain outside the handoff.
