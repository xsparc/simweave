# Verification scope

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
PR #43 merged during implementation; this milestone now builds on its squash commit on main.
