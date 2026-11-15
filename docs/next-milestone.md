# Next milestone: retained bundle targets and explicit verification scope

Status: planned handoff, 2026-11-15. TC030, SW037 and EF-015 complete the
[previous five tasks](governance/handoff-2026-11-15.md).

1. **ToolCapsule TC031: normalized bundle identity contract.** Define a versioned deterministic summary-bundle encoding, SHA-256/byte-count record, closed bounded reader and schema. Pin a golden vector and distinguish normalized content identity from source-file bytes and signatures.
2. **ToolCapsule TC031: identity-gated bundle review.** Add exclusive identity export and mutually exclusive digest/file checks to bundle verification, rendering and exact export verification. Compose with independent summaries and add a synthetic portable CLI workflow covering replacement, collisions and unchanged inputs.
3. **SimWeave SW038: explicit verification scope output.** Add documented source_checked and identity_checked booleans to successful bundle verification responses, derived from checks actually performed. Cover all standalone/source/digest/file combinations and preserve errors and read-only behavior; validity alone must not imply independent verification.
4. **EdgeForge EF-016: standalone retained bundle identity check.** Add a bounded read-only record-validation command with fixed output, rejecting malformed/duplicate/oversized records without reading a bundle or invoking inference. Extend the synthetic portable workflow to exercise invalid records and byte preservation.
5. **EdgeForge EF-016: explicit verification scope output.** Report source_checked and identity_checked on successful bundle and exact export verification. Cover each gate combination and ensure replacement evidence cannot acquire a source-checked result without matching independently supplied reports.

Planned only. Retain source and identity targets independently. These checks do not
establish authorship, original source-file identity or runtime authority. Recheck
merged bases; EdgeForge's foundation stack remains open.
