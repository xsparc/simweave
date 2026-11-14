# ADR 0034: Identity file export

Status: accepted
Date: 2026-11-15

## Decision

```sh
simweave sweep-bundle-identity bundle.json --output identity.json
python examples/portable_review.py review-demo
```

Omitting --output preserves the existing stdout JSON record. With --output, the
same version-1 identity record is serialized as pretty UTF-8 JSON plus LF and
validated against the existing closed reader and 4096-byte bound before exclusive
creation. Successful file export has no stdout. Invalid bundles and existing output
paths fail without replacing retained evidence. The portable synthetic example now
uses this CLI export for original and replacement identities. No simulation runs.
Identity is normalized content identity, not a signature or original-file hash.

## Alternatives and acceptance

Reuse strict validators and existing serializers instead of introducing a second interpretation of retained evidence. Exclusive output avoids replacing prior evidence. Acceptance is in `tests/test_identity_export.py`, `tests/test_bundle_html.py`. Bounds, malformed input, replacement and byte preservation are covered; runtime execution remains outside these review commands.
