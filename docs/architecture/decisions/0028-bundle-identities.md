# ADR 0028: Bundle identities

Status: accepted
Date: 2026-11-07

## Decision

The `simweave-plan-bundle-json-v1` identity profile hashes the existing validated bundle exporter bytes. It includes the complete normalized model, sorted keys, compact separators, ASCII escaping, finite Python JSON numbers and exactly one terminal LF. The LF participates in SHA-256. Numeric values follow the validated model and Python encoder, including negative zero; this is not RFC 8785/JCS or a promise of cross-language number serialization. Changing these rules requires a new profile.

```sh
simweave sweep-bundle examples/plan-review/before.json examples/plan-review/after.json --output bundle.json
simweave sweep-bundle-identity bundle.json
simweave sweep-bundle-verify bundle.json --expected-sha256 EXPECTED_DIGEST
simweave sweep-bundle-render bundle.json --format html --output review.html --expected-sha256 EXPECTED_DIGEST
```

The identity summary contains schema_version=1, canonicalization, bundle_sha256, bytes and interpretation=retained_identity_not_attestation. It differs from original-file hashes and embedded plan/Suite hashes. Formatting and object-key order normalize identically; changed seeds, reversed sources or consistent envelope replacement can change identity even with equal workload counts.

`--expected-sha256` accepts exactly 64 lowercase hexadecimal characters. It also applies to `sweep-bundle`, `sweep-bundle-verify-sources` and `sweep-bundle-verify-csv`. Validation happens before review output or exclusive file creation. Mismatch returns 2 with fixed diagnostics; existing verification summaries and calls without the option retain their behavior. The identity command prints a summary only after validation.

SDK `bundle_identity` and `verify_bundle_identity` revalidate nested models through the existing exporter. Bundle intake/export stays bounded to 192 KiB, component plans and renderings to 64 KiB. No simulation, repair or evidence rewrite occurs. Retain expected digests independently; digest consistency does not authenticate authorship, prove source-plan agreement or establish observed simulation results. Use explicit source verification separately.

## Alternatives and acceptance

Reuse the existing normalized exporters and semantic validators rather than trusting
self-reported fields or changing established byte profiles. Raw file-byte hashes
cannot substitute for normalized identity. Strict structural decoding precedes
semantic checks. Validation covers successful round trips, equivalent formatting,
whole-record replacement, direction, malformed/oversized evidence, SDK mutations
where applicable, fixed diagnostics and failure before any output write.

No runtime capability, simulator behavior, source admission, signing or deployment
change is included. The saved conversation-approved milestone defines this scope.
