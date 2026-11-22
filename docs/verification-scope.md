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

## Response contract

`simweave sweep-bundle-verification-schema` prints the same version 1 JSON
Schema as [the checked-in schema](../schemas/bundle-verification-response.schema.json).
The four verification commands keep the same fields, meanings, and exit outcomes.

Python callers can pass their verification response bytes to
`simweave.verification_response.read_bundle_verification_response`. The reader
rejects unknown or missing fields, duplicate keys, unsupported versions, incorrect
types, and claims beyond local source consistency. It accepts at most 4 KiB;
callers reading an arbitrary stream should also bound that read to 4 KiB plus one
byte to detect over-limit input. JSON Schema describes the JSON data model; the
Python reader additionally checks the encoded byte limit, duplicate keys, and
the exact integer representation of the version. A parsed response is not proof
that the stated checks ran. For independent evidence, rerun the verifier against
separately retained inputs or a separately trusted identity.
