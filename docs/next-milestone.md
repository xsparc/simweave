# Next milestone: retained bundle identities and portable summaries

Status: planned handoff, 2026-11-13. TC028, SW035 and EF-013 complete the
[previous five tasks](governance/handoff-2026-11-12.md).

1. **ToolCapsule TC029: portable summary bundle contract.** Define a closed versioned envelope containing before/after configuration summaries and their derived difference. Reuse strict readers, bound components and envelope, expose a schema, and reject duplicates, inconsistent differences and unsupported versions without guest execution.
2. **ToolCapsule TC029: summary bundle export and verification.** Add exclusive export and read-only verification for the envelope, optionally comparing independent summary files. Test source reversal, consistent replacement, failed configuration evidence and unchanged inputs.
3. **SimWeave SW036: exclusive identity-file export.** Add optional bounded output to bundle identity generation while retaining stdout behavior. Reuse the existing closed record and exclusive creation, test invalid bundle/no output and collisions, and update the portable example to use the CLI export.
4. **EdgeForge EF-014: normalized bundle identity.** Define a versioned deterministic encoding and SHA-256 identity for comparison bundles, with strict expected-digest gates on verification and rendering. Distinguish normalized identity from original file bytes, compose with source checks and pin a golden vector.
5. **EdgeForge EF-014: exact bundle export verification.** Add bounded read-only verification of retained HTML/CSV against a validated comparison bundle, optionally checking independent sources and expected identity. Reuse existing renderers, reject post-export edits and prove no inference.

Planned only. Independent sources and identity targets remain necessary for
substitution detection. Recheck merged bases before implementation, especially
EdgeForge's open foundation stack. No merge, release or deployment authority.
