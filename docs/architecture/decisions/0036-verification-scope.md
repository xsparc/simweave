# ADR 0036: Verification scope

Status: accepted
Date: 2026-11-18

## Decision

Successful sweep-bundle-verify, sweep-bundle-verify-sources, sweep-bundle-verify-html
and sweep-bundle-verify-csv responses now include two additive booleans:

- source_checked: independent before/after plans were supplied and matched.
- identity_checked: a supplied digest or retained identity record matched.

Standalone verification reports both false. Source verification always reports
source_checked true after success; HTML/CSV checks report it only with a complete
source pair. A valid replacement bundle with its own matching identity can report
identity_checked true and source_checked false. Original independent sources still
reject that replacement. Any failure returns the existing sanitized error with no
successful verification response. No input is modified and no simulation runs.

The schema_version, verified and interpretation fields remain unchanged. These
booleans describe checks actually completed, not authenticity or attestation.
This branch builds on unmerged identity-record-check PR #43; no merge is implied.

## Alternatives and acceptance

Reuse existing validators and keep interpretation explicit rather than silently inferring trust or executing workloads. Acceptance: `tests/test_verification_scope.py`. Synthetic fixtures, malformed input, bounded work and byte preservation are required.
