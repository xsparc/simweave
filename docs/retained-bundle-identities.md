# Retained bundle identities

The closed `BundleIdentity` contract describes the existing five-field identity summary. It requires integer schema_version=1, the simweave-plan-bundle-json-v1 profile, a lowercase 64-character hexadecimal bundle_sha256, integer bytes from 1 through 196608, and interpretation=retained_identity_not_attestation. Missing or unknown fields, coercible versions/counts, duplicate keys and malformed input are rejected. The checked-in JSON schema matches the executable contract.

```sh
simweave sweep-bundle-identity-schema
simweave sweep-bundle-identity bundle.json > identity.json
simweave sweep-bundle-verify bundle.json --identity identity.json
simweave sweep-bundle-render bundle.json --format html --identity identity.json --output review.html
```

`--identity` is also supported by bundle creation, explicit-source verification and CSV verification. It is mutually exclusive with `--expected-sha256`. The file is bounded to 4096 bytes before parsing; both canonical digest and byte count must match before verification output, rendering or exclusive creation. Existing identity generation fields and canonical bytes are unchanged. Shell redirection is shell-managed; choose a new identity filename when retaining output.

SDK `read_bundle_identity` and `verify_bundle_identity_record` apply the same rules and revalidate caller-owned models. Equivalent JSON whitespace and key ordering are accepted. A whole internally consistent replacement still fails against an independently retained record. No simulation or input rewrite occurs. Existing bundle/component/output limits remain in force.

Retained identity is not a signature, source-plan agreement or proof of observed simulation results. Keep identity files independently and use explicit-source checks when source consistency is required.
