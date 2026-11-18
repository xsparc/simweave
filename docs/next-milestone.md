# Next milestone: explicit verification contracts and richer trace evidence

Status: planned handoff, 2026-11-18. TC031, SW038 and EF-016 complete the saved
[shared handoff](governance/handoff-2026-11-18.md); CausalSpan CS-002 completes its
five-item external OTLP compatibility milestone.

1. **ToolCapsule TC032: explicit bundle verification scope.** Add source_checked and identity_checked to successful bundle and exact-export verification output. Cover standalone, digest, identity-file and independent-summary combinations; never emit successful scope for a failed check.
2. **SimWeave SW039: verification response contract.** Publish a versioned schema and closed reader for bundle verification responses, distinguishing successful execution scope from independent evidence. Add schema/CLI parity and malformed-field tests without changing retained bundle encodings.
3. **CausalSpan CS-006: event and link evidence.** Preserve and validate event timestamps and span links from external OTLP, including ID/types and bounded collections. Keep links distinct from parent edges and reject malformed evidence without live calls.
4. **CausalSpan CS-006: resource/scope inspection.** Add opt-in CLI grouping by preserved resource/service and instrumentation scope, with deterministic counts and escaped timeline labels. Preserve default summary behavior, avoid token double-counting and test multiple resources/scopes and hostile labels.
5. **EdgeForge EF-017: verification response contract.** Publish a versioned schema and closed reader for bundle/export verification responses with source_checked and identity_checked. Pin CLI parity, reject unsupported types/claims, and keep record validation distinct from executed checks.

Planned only. Independently retained sources and identity targets are required to
detect substitution. Verification responses do not establish authorship or runtime
authority. Recheck merged bases, including SimWeave #43 and EdgeForge's foundation
stack, before the next run. No merges, releases or deployments are authorized.
