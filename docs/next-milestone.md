# Next milestone: retained review identity and HTML verification

Status: planned handoff, 2026-11-10. TC025, SW032 and EF-010 complete the
[previous five tasks](governance/handoff-2026-11-09.md). This shared tracker is
copied into all three repositories and milestone PRs.

1. **ToolCapsule TC026: canonical difference identity.** Define a versioned deterministic encoding and SHA-256 identity for validated retained differences. Preserve summary/source limits, distinguish normalized identity from original-file bytes, and test equivalent formatting, reversal and consistent replacement.
2. **ToolCapsule TC026: expected-identity review gate.** Accept an optional strict expected digest before difference checking and HTML/CSV export, composed with independent summary checks. Reject mismatches before output and preserve all existing command behavior without the option.
3. **SimWeave SW033: executable portable review guide.** Add a synthetic example through bundle creation, identity retention, explicit-source HTML/CSV rendering and CSV verification. Prove replacement rejection, input preservation and no simulation during review.
4. **SimWeave SW033: retained HTML verification.** Verify exact HTML bytes against a validated bundle, with optional source/identity gates and bounded read-only intake. Reject edited content, CSP/style changes and line-ending changes without repair or browser execution.
5. **EdgeForge EF-011: retained HTML verification.** Verify exact HTML bytes against a validated comparison and explicit report sources, optionally checking a retained identity record. Reuse the existing renderer and test wrong sources with matching identity, altered markup/CSP and no inference.

Priority: detect post-export edits and preserve independently retained review
targets. Exact-render verification is format-version-sensitive, not signature
verification. Inspect merged state before branching, especially EdgeForge's open
foundational stack. Planned only; merge, deployment, release and signing require
separate authorization.
