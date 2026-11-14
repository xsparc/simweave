# Next milestone: portable bundle review and retained identity checks

Status: planned handoff, 2026-11-15. TC029, SW036 and EF-014 complete the
[previous five tasks](governance/handoff-2026-11-13.md).

1. **ToolCapsule TC030: bundle review rendering.** Render validated summary bundles as bounded HTML/CSV using existing difference renderers, with paired independent summaries and exclusive output. Keep source-check status explicit and test hostile values and failed configuration evidence.
2. **ToolCapsule TC030: exact bundle export verification.** Verify retained HTML/CSV bytes against the validated bundle and optional independent summaries. Bound reads, reject edits and consistent replacement, preserve all inputs and prove no guest execution.
3. **SimWeave SW037: standalone retained identity validation.** Add a bounded read-only command for the existing closed identity record, with fixed success/error output. Cover duplicate fields, version/type errors and invalid digest/size; distinguish record validity from matching any bundle. Extend the portable example with malformed retained identity rejection.
4. **EdgeForge EF-015: retained bundle identity contract.** Add a closed versioned reader and schema for the existing normalized bundle identity record, bounded exclusive file export, and schema/reader parity plus golden-vector regression coverage.
5. **EdgeForge EF-015: identity-file review gates.** Accept retained identity records on bundle verification, rendering and exact export verification, composing with independent source checks. Reject ambiguous simultaneous digest/file gates, malformed records and consistent replacement; exercise a portable synthetic CLI workflow without inference.

Planned only. Identity and source targets must be retained independently to detect
substitution; none establishes authorship or runtime authority. Recheck merged
bases before implementation, especially EdgeForge's open foundation stack.
